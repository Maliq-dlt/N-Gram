"""Small, real Auto/CPU/CUDA LoRA pilot. Keeps base weights and saves reproducible evidence."""

from __future__ import annotations

import hashlib
import json
import random
import time
from typing import cast

from chat import SYSTEM
from runtime import CHAT_ADAPTER, CHAT_BASE, MODELS, ROOT, select_device


def train(device: str, adapter):
    import torch
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.set_num_threads(8)
    torch.manual_seed(42)
    random.seed(42)
    data_path = ROOT / "training_chat.json"
    rows = json.loads(data_path.read_text(encoding="utf-8"))["rows"]
    assert len({r["user"] for r in rows}) == len(rows)
    tokenizer = AutoTokenizer.from_pretrained(CHAT_BASE, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        CHAT_BASE,
        local_files_only=True,
        dtype=torch.bfloat16 if device.startswith("cuda") else torch.float32,
        attn_implementation="sdpa",
    )
    cast(torch.nn.Module, model).to(device)
    model.config.use_cache = False

    def encode(row):
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": row["user"]}]
        prefix = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, enable_thinking=False
        )
        completion = tokenizer.encode(
            row["assistant"] + tokenizer.eos_token, add_special_tokens=False
        )
        full = prefix + completion
        assert (
            len(full) <= 512
            and tokenizer.decode(completion) == row["assistant"] + tokenizer.eos_token
        )
        labels = [-100] * len(prefix) + full[len(prefix) :]
        assert any(label != -100 for label in labels) and all(
            label == -100 for label in labels[: len(prefix)]
        )
        return {
            "input_ids": torch.tensor([full], device=device),
            "attention_mask": torch.ones((1, len(full)), dtype=torch.long, device=device),
            "labels": torch.tensor([labels], device=device),
        }

    train = [encode(r) for r in rows if r["split"] == "train"]
    heldout = [encode(r) for r in rows if r["split"] == "eval"]

    def loss_value():
        model.eval()
        with torch.inference_mode():
            return sum(float(model(**batch).loss) for batch in heldout) / len(heldout)

    def responses():
        torch.manual_seed(123)
        model.eval()
        answers = []
        for row in [r for r in rows if r["split"] == "eval"][:3]:
            inputs = tokenizer.apply_chat_template(
                [{"role": "system", "content": SYSTEM}, {"role": "user", "content": row["user"]}],
                tokenize=True,
                add_generation_prompt=True,
                enable_thinking=False,
                return_dict=True,
                return_tensors="pt",
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}
            with torch.inference_mode():
                output = model.generate(
                    **inputs,
                    max_new_tokens=100,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.8,
                    top_k=20,
                    pad_token_id=tokenizer.eos_token_id,
                    use_cache=True,
                )
            answers.append(
                {
                    "question": row["user"],
                    "answer": tokenizer.decode(
                        output[0, inputs["input_ids"].shape[1] :], skip_special_tokens=True
                    ),
                }
            )
        return answers

    started = time.monotonic()
    baseline_loss = loss_value()
    baseline_responses = responses()
    print("Baseline heldout loss:", baseline_loss, flush=True)
    torch.manual_seed(42)
    model = get_peft_model(
        model,
        LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=8,
            lora_alpha=16,
            lora_dropout=0.05,
            target_modules=["q_proj", "v_proj"],
            bias="none",
        ),
    )
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=2e-4)
    losses = []
    for epoch in range(2):
        model.train()
        random.shuffle(train)
        for step, batch in enumerate(train, 1):
            optimizer.zero_grad(set_to_none=True)
            loss = model(**batch).loss
            if not torch.isfinite(loss):
                raise RuntimeError("Training loss is nonfinite.")
            loss.backward()
            torch.nn.utils.clip_grad_norm_((p for p in model.parameters() if p.requires_grad), 1.0)
            optimizer.step()
            losses.append(float(loss.detach()))
            print(f"Epoch {epoch + 1}/2 step {step}/{len(train)} loss={losses[-1]:.4f}", flush=True)
    final_loss = loss_value()
    final_responses = responses()
    model.save_pretrained(str(adapter))
    tokenizer.save_pretrained(adapter)
    report = {
        "scope": "Real pilot LoRA; 32 manual synthetic training examples and 6 phrase-heldout examples. Not factory or broad conversational validation.",
        "seed": 42,
        "epochs": 2,
        "steps": len(losses),
        "learning_rate": 2e-4,
        "dtype": "bfloat16" if device.startswith("cuda") else "float32",
        "device": device,
        "gpu_peak_memory_mb": round(torch.cuda.max_memory_allocated() / 2**20, 2)
        if device.startswith("cuda")
        else None,
        "trainable_parameters": trainable,
        "prompt_masked": True,
        "train_examples": len(train),
        "eval_examples": len(heldout),
        "baseline_loss": baseline_loss,
        "adapter_loss": final_loss,
        "step_losses": losses,
        "baseline_responses": baseline_responses,
        "adapter_responses": final_responses,
        "seconds": round(time.monotonic() - started, 2),
        "dataset_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
        "adapter_sha256": hashlib.sha256(
            (adapter / "adapter_model.safetensors").read_bytes()
        ).hexdigest(),
        "base_revision": json.loads((MODELS / "manifest.json").read_text(encoding="utf-8"))["chat"][
            "revision"
        ],
    }
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    report_name = "chat_pilot.json" if adapter == CHAT_ADAPTER else f"training_{adapter.name}.json"
    if adapter == CHAT_ADAPTER:
        manifest_path = MODELS / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["chat"].update(
            fine_tuned=True,
            adapter=adapter.name,
            adapter_sha256=report["adapter_sha256"],
            validation="pilot only",
        )
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    report["adapter"] = adapter.name
    (reports / report_name).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )
    print(
        f"Saved real adapter. Heldout loss {baseline_loss:.4f} -> {final_loss:.4f}. {report['seconds']}s",
        flush=True,
    )
    return report


def main():
    import argparse
    import gc
    import re
    from datetime import UTC, datetime

    import torch

    parser = argparse.ArgumentParser(description="Training LoRA lokal; Auto memilih CUDA/CPU.")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument(
        "--output-name", help="Nama folder adapter kandidat di models/. Tidak menimpa hasil lama."
    )
    args = parser.parse_args()
    name = args.output_name or (
        CHAT_ADAPTER.name
        if not CHAT_ADAPTER.exists()
        else "chat-candidate-" + datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    )
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", name):
        parser.error("Nama output hanya huruf, angka, garis bawah, dan tanda hubung.")
    adapter = MODELS / name
    if adapter.exists():
        parser.error(
            "Folder output sudah ada. Pilih nama kandidat baru agar hasil lama tetap utuh."
        )
    device, reason = select_device(args.device, 6.0)
    print("Training:", device, reason, flush=True)
    fallback = False
    try:
        report = train(device, adapter)
    except torch.cuda.OutOfMemoryError:
        if device == "cpu":
            raise
        fallback = True
    if fallback:
        gc.collect()
        torch.cuda.empty_cache()
        device, reason = "cpu", "VRAM habis saat training; training diulang dari base di CPU"
        print(reason, flush=True)
        report = train(device, adapter)
    report["device_reason"] = reason
    report["device_preference"] = args.device
    report_name = "chat_pilot.json" if adapter == CHAT_ADAPTER else f"training_{adapter.name}.json"
    (ROOT / "reports" / report_name).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
