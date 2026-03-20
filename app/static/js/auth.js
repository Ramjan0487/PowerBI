/* auth.js — login form, mTLS badge, shared auth utilities */
(function(){
  // mTLS status check
  const mtlsLabel = document.getElementById('mtlsLabel');
  const mtlsDot   = document.getElementById('mtlsDot') || document.querySelector('.mtls-dot');
  if(mtlsLabel){
    fetch('/auth/cert-status',{credentials:'same-origin'})
      .then(r=>r.json())
      .then(d=>{
        if(d.verified){
          mtlsLabel.textContent='mTLS certificate verified';
          if(mtlsDot) mtlsDot.style.background='#22c55e';
        } else {
          mtlsLabel.textContent='No client certificate';
          if(mtlsDot) mtlsDot.style.background='#f59e0b';
        }
      }).catch(()=>{ if(mtlsLabel) mtlsLabel.textContent='Certificate check unavailable'; });
  }

  // Login form
  const loginForm = document.getElementById('loginForm');
  if(loginForm){
    const pwToggle = document.getElementById('pwToggle');
    if(pwToggle) pwToggle.addEventListener('click',()=>{
      const pw = document.getElementById('password');
      const show = pw.type==='password';
      pw.type = show?'text':'password';
      pwToggle.textContent = show?'Hide':'Show';
    });

    loginForm.addEventListener('submit', async(e)=>{
      e.preventDefault();
      const email    = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value;
      const errDiv   = document.getElementById('formError');
      const btnTxt   = document.getElementById('btnTxt');
      const btnSpin  = document.getElementById('btnSpin');
      const btn      = document.getElementById('loginBtn');

      if(!email || !password){ showErr(errDiv,'Email and password are required.'); return; }

      btnTxt.textContent='Signing in…'; btnSpin.classList.remove('hidden'); btn.disabled=true;
      errDiv.classList.add('hidden');

      try{
        const res = await fetch('/auth/login',{
          method:'POST', credentials:'same-origin',
          headers:{'Content-Type':'application/json','Accept':'application/json'},
          body:JSON.stringify({email,password})
        });
        const data = await res.json();
        if(res.ok && data.redirect){ window.location.href=data.redirect; }
        else { showErr(errDiv, data.message||'Login failed. Please try again.'); }
      } catch { showErr(errDiv,'Network error. Please check your connection.'); }
      finally { btnTxt.textContent='Sign In'; btnSpin.classList.add('hidden'); btn.disabled=false; }
    });

    // Cert login button
    const certBtn = document.getElementById('certLoginBtn');
    if(certBtn) certBtn.addEventListener('click',()=>{
      document.getElementById('loginForm').dispatchEvent(new Event('submit'));
    });
  }

  function showErr(el, msg){
    if(!el) return;
    el.textContent=msg;
    el.classList.remove('hidden');
  }
})();
