/* LC76 LIBRARY — shared script (Design Guidelines v2.0).
   Section menu: lights the section you are reading and slides the menu
   sideways so that item is always in view. Works with every menu pattern
   in the library (onclick getElementById, data-target, go('…')). */
(function(){
  function bar(){return document.querySelector('.toc-bar,#tocBar,.toc')}
  function targetOf(el){
    var d=el.getAttribute('data-target'); if(d) return d;
    var on=el.getAttribute('onclick')||'', m=on.match(/(?:getElementById|go|scrollToSection)\(\s*['"]([^'"]+)['"]/);
    if(m) return m[1];
    var h=el.getAttribute('href')||''; if(h.charAt(0)==='#'&&h.length>1) return h.slice(1);
    return null;
  }
  function setup(){
    var b=bar(); if(!b) return;
    var items=[].slice.call(b.querySelectorAll('a,button,span')).map(function(el){
      var id=targetOf(el), sec=id&&document.getElementById(id); return sec?{el:el,sec:sec}:null;
    }).filter(Boolean);
    if(!items.length) return;
    var current=null, ticking=false;
    function pinnedHeight(){
      var u=b.closest('.sticky-nav-unit,.sticky-wrap,#sticky-nav')||b; return u.getBoundingClientRect().bottom;
    }
    function update(){
      ticking=false;
      var line=pinnedHeight()+24, active=items[0];
      for(var i=0;i<items.length;i++){ if(items[i].sec.getBoundingClientRect().top<=line) active=items[i]; }
      if((window.innerHeight+window.scrollY)>=document.documentElement.scrollHeight-4) active=items[items.length-1];
      if(active===current) return;
      if(current){ current.el.classList.remove('lc-active'); current.el.removeAttribute('aria-current'); }
      current=active; active.el.classList.add('lc-active'); active.el.setAttribute('aria-current','true');
      var left=active.el.offsetLeft-(b.clientWidth-active.el.offsetWidth)/2;
      try{ b.scrollTo({left:Math.max(0,left),behavior:'smooth'}); }catch(e){ b.scrollLeft=Math.max(0,left); }
    }
    window.addEventListener('scroll',function(){ if(!ticking){ ticking=true; requestAnimationFrame(update);} },{passive:true});
    window.addEventListener('resize',update);
    update();
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',setup); else setup();
})();

/* Print type: fetch the print faces up front, so a PDF made straight away
   never falls back to a system font. */
(function(){
  if(!document.fonts||!document.fonts.load) return;
  ['400 10pt Oswald','600 10pt Oswald','700 10pt Oswald','400 10pt "Bebas Neue"','400 10pt "IBM Plex Mono"','600 10pt "IBM Plex Mono"']
    .forEach(function(f){ try{ document.fonts.load(f); }catch(e){} });
})();

/* Wide tables: on a phone, a table wider than its box scrolls sideways
   inside it (class lc-scroll, styled in LC76_Library.css). Re-checked when
   the screen turns or a hidden section opens.
   Where a phone squeezes a column of long text (notes, descriptions) under
   140 px, that table's columns are marked once by the length of their
   longest cell — lc-col-long (120+ characters), lc-col-wide (60+) or
   lc-col-mid (28+) — so they keep a readable width and the table scrolls
   instead of squeezing them to a few words a line (13 Oct 2026). */
(function(){
  var pending=false;
  function widen(t){
    if(t.getAttribute('data-lc-cols')||window.innerWidth>767||!t.offsetWidth) return;
    var rows=t.rows, mx=[], w=[], c, r, k, cell, tight=false;
    for(r=0;r<rows.length;r++){ c=0;
      for(k=0;k<rows[r].cells.length;k++){ cell=rows[r].cells[k];
        if((cell.colSpan||1)===1){
          var L=cell.textContent.replace(/\s+/g,' ').trim().length, cw=cell.getBoundingClientRect().width;
          if(!(mx[c]>=L)) mx[c]=L; if(cw&&!(w[c]<=cw)) w[c]=cw; }
        c+=cell.colSpan||1; } }
    for(c=0;c<mx.length;c++) if(mx[c]>=60&&w[c]<140) tight=true;
    t.setAttribute('data-lc-cols',tight?'1':'0'); if(!tight) return;
    for(r=0;r<rows.length;r++){ c=0;
      for(k=0;k<rows[r].cells.length;k++){ cell=rows[r].cells[k];
        if((cell.colSpan||1)===1){
          if(mx[c]>=120) cell.classList.add('lc-col-long');
          else if(mx[c]>=60) cell.classList.add('lc-col-wide');
          else if(mx[c]>=28) cell.classList.add('lc-col-mid'); }
        c+=cell.colSpan||1; } }
    t.classList.add('lc-cols');
  }
  function check(){
    pending=false;
    [].forEach.call(document.querySelectorAll('table'),function(t){
      widen(t);
      t.classList.remove('lc-scroll');
      var box=t.parentElement; if(!box||!t.offsetWidth) return;
      if(t.scrollWidth>box.clientWidth+1||t.offsetWidth>box.clientWidth+1) t.classList.add('lc-scroll');
    });
  }
  function soon(){ if(!pending){ pending=true; setTimeout(check,60); } }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',check); else check();
  window.addEventListener('load',soon); window.addEventListener('resize',soon);
  document.addEventListener('click',soon,true); document.addEventListener('toggle',soon,true);
})();
