async function askAI(){
  const input=document.getElementById("aiQuestion"), box=document.getElementById("aiAnswer");
  const q=input.value.trim(); if(!q)return;
  box.classList.remove("d-none"); box.innerText="Campus AI is thinking...";
  const r=await fetch("/api/assistant",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:q})});
  const data=await r.json(); box.innerText=data.answer;
}
function quickAsk(q){document.getElementById("aiQuestion").value=q;askAI();}
