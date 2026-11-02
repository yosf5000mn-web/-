(function(){
  const key='raqmyat-theme';
  const saved=localStorage.getItem(key);
  if(saved) document.documentElement.dataset.theme=saved;
  const toggle=document.getElementById('themeToggle');
  if(toggle) toggle.addEventListener('click',()=>{
    const next=document.documentElement.dataset.theme==='dark'?'light':'dark';
    document.documentElement.dataset.theme=next; localStorage.setItem(key,next);
  });
  document.querySelectorAll('[data-copy]').forEach(btn=>btn.addEventListener('click',async()=>{
    try{await navigator.clipboard.writeText(btn.dataset.copy);btn.textContent='تم النسخ';}
    catch(e){btn.textContent='انسخ يدوياً';}
  }));
})();
