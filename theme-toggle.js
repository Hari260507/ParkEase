(function(){
  const key='parkease-theme';
  function apply(theme){document.documentElement.setAttribute('data-theme',theme);try{localStorage.setItem(key,theme)}catch(e){};const b=document.querySelector('.theme-toggle');if(b){b.innerHTML=theme==='dark'?'☀️ Light mode':'🌙 Dark mode';b.setAttribute('aria-label',theme==='dark'?'Switch to light mode':'Switch to dark mode')}}
  let initial='dark';try{initial=localStorage.getItem(key)||'dark'}catch(e){}apply(initial);
  function add(){if(document.querySelector('.theme-toggle'))return;const b=document.createElement('button');b.type='button';b.className='theme-toggle';b.addEventListener('click',()=>apply(document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark'));document.body.appendChild(b);apply(document.documentElement.getAttribute('data-theme')||initial)}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',add);else add();
})();
