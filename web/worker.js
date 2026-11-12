/* OES-1000: legacy-compatible browser worker plus native estimator registry. */
const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.27.2/full/";
const FILES = ["__init__.py","_causal_core.py","_diff_gmm.py","_ml_core.py","_panel_core.py","_panel_tests.py",
"bayes.py","causal.py","core.py","markov.py","ml.py","panel.py","pvar.py","statespace_var.py","timeseries.py"];
const ROOT = new URL("../src/oes1000/legacy/oes_engine/", self.location.href);
const BASE = ["numpy","pandas","scipy","statsmodels"];
const NATIVE_FILES = [
  ["__init__.py","src/oes1000/__init__.py"],
  ["registry.py","src/oes1000/registry.py"],
  ["api.py","src/oes1000/api.py"],
  ["classical/__init__.py","src/oes1000/classical/__init__.py"],
  ["classical/ols.py","src/oes1000/classical/ols.py"],
  ["classical/linear.py","src/oes1000/classical/linear.py"],
  ["classical/discrete.py","src/oes1000/classical/discrete.py"],
  ["classical/glm_extra.py","src/oes1000/classical/glm_extra.py"],
  ["classical/advanced_discrete.py","src/oes1000/classical/advanced_discrete.py"]
];
let py=null, booting=null; const loaded=new Set();
const say=text=>postMessage({type:"status",text});
async function boot(version){
 importScripts(PYODIDE+"pyodide.js"); say("Starting Python in your browser…");
 py=await loadPyodide({indexURL:PYODIDE});
 say("Loading NumPy, pandas, SciPy and statsmodels…"); await py.loadPackage(BASE); BASE.forEach(p=>loaded.add(p));
 say("Loading the existing OES estimation engine…"); py.FS.mkdirTree("/oes_engine");
 for(const f of FILES){const url=new URL(f,ROOT);const r=await fetch(url);if(!r.ok)throw new Error("Could not load engine file "+f+" ("+r.status+").");py.FS.writeFile("/oes_engine/"+f,await r.text());}
 py.runPython("import sys; sys.path.insert(0, '/'); import oes_engine");
 say("Loading the OES-1000 native estimator registry…"); py.FS.mkdirTree("/oes1000/classical");
 for(const [target,source] of NATIVE_FILES){
  const url=new URL("../"+source,self.location.href);
  const r=await fetch(url);if(!r.ok)throw new Error("Could not load native estimator module "+source+" ("+r.status+").");
  py.FS.writeFile("/oes1000/"+target,await r.text());
 }
 py.runPython("import oes1000; import oes1000.api");
 return py.runPython("oes_engine.__version__");
}
async function ensure(packages){
 const requested=packages||[];
 if(requested.includes("xgboost"))throw new Error("XGBoost is not currently available in the standard Pyodide browser runtime. The other legacy OES estimators use the local Python engine.");
 const need=requested.filter(p=>!loaded.has(p));
 if(need.length){say("Loading "+need.join(", ")+"…");await py.loadPackage(need);need.forEach(p=>loaded.add(p));}
}
onmessage=async e=>{
 const m=e.data||{};
 try{
  if(!booting)booting=boot(m.version||"1").catch(err=>{booting=null;py=null;throw err;});
  const version=await booting;
  if(m.cmd==="init"){postMessage({type:"ready",version});return;}
  if(m.cmd==="native_run"){
   await ensure(["numpy","pandas","scipy"]);say("Estimating "+m.model+" with the native OES-1000 registry…");
   py.globals.set("oes_native_model",m.model);py.globals.set("oes_native_csv",m.csv);
   py.globals.set("oes_native_spec",JSON.stringify(m.spec||{}));
   const t0=performance.now();
   const out=py.runPython("oes1000.api.estimate_csv(oes_native_csv, oes_native_model, oes_native_spec)");
   postMessage({type:"native_result",job:m.job,result:JSON.parse(out),seconds:(performance.now()-t0)/1000});
   return;
  }
  if(m.cmd==="run"){
   await ensure(m.packages);say("Estimating "+m.model+"…");
   py.globals.set("oes_model",m.model);py.globals.set("oes_csv",m.csv);py.globals.set("oes_spec",JSON.stringify(m.spec||{}));
   const t0=performance.now();const out=py.runPython("oes_engine.run_json(oes_model, oes_csv, oes_spec)");
   postMessage({type:"result",job:m.job,result:JSON.parse(out),seconds:(performance.now()-t0)/1000});
  }
 }catch(err){postMessage({type:"error",job:m.job,error:String(err&&err.message||err)});}
};
