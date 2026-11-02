
const themeBtn=document.getElementById('themeToggle');
if(themeBtn){if(localStorage.getItem('raqmiat-theme')==='light')document.body.classList.add('light');themeBtn.addEventListener('click',()=>{document.body.classList.toggle('light');localStorage.setItem('raqmiat-theme',document.body.classList.contains('light')?'light':'dark')})}
