// Render real React components for structural regression checks without a browser.
const path=require('node:path'),esbuild=require('esbuild');
const bundle=esbuild.buildSync({entryPoints:[path.join(__dirname,'../frontend/App.tsx')],bundle:true,platform:'node',format:'cjs',jsx:'automatic',packages:'external',write:false});
const rendered={exports:{}};
new Function('require','module','exports',bundle.outputFiles[0].text)(require,rendered,rendered.exports);
module.exports=require('react-dom/server').renderToStaticMarkup(require('react').createElement(rendered.exports.App));
