try{const t=localStorage.getItem("video-theme")||"system";document.documentElement.dataset.theme=t==="system"?(matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"):t}catch{}
