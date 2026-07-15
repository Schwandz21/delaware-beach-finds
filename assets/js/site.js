(function(){
 const c=window.DBF_CONFIG||{};
 const validShopify=c.shopifyUrl && !c.shopifyUrl.includes('YOUR-SHOPIFY');
 function withUtm(url, campaign){
   try{const u=new URL(url);u.searchParams.set('utm_source','delawarebeachfinds');u.searchParams.set('utm_medium','website');u.searchParams.set('utm_campaign',campaign||'sitewide');return u.toString()}catch(e){return url}
 }
 document.querySelectorAll('[data-instagram-link]').forEach(a=>a.href=withUtm(c.instagramUrl,'instagram'));
 document.querySelectorAll('[data-etsy-link]').forEach(a=>a.href=withUtm(c.etsyUrl,'etsy_shop'));
 document.querySelectorAll('[data-shopify-link]').forEach(a=>{
   if(validShopify){a.href=withUtm(c.shopifyUrl,'shopify_store')}else{a.href=(a.dataset.fallback||'shop.html');a.title='Add your Shopify URL in assets/js/config.js before launch';}
 });
 document.querySelectorAll('[data-contact-email]').forEach(a=>{a.href='mailto:'+c.contactEmail;a.textContent=c.contactEmail});
 document.querySelectorAll('[data-year]').forEach(el=>el.textContent=new Date().getFullYear());
 const t=document.querySelector('.menu-toggle'),n=document.querySelector('.nav-links');if(t&&n)t.addEventListener('click',()=>{const o=n.classList.toggle('open');t.setAttribute('aria-expanded',o?'true':'false')});
 document.querySelectorAll('a[target="_blank"]').forEach(a=>a.setAttribute('rel','noopener noreferrer'));
 if(c.googleAnalyticsId){const g=document.createElement('script');g.async=true;g.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(c.googleAnalyticsId);document.head.appendChild(g);window.dataLayer=window.dataLayer||[];window.gtag=function(){dataLayer.push(arguments)};gtag('js',new Date());gtag('config',c.googleAnalyticsId);}
 const f=document.querySelector('[data-newsletter-form]');if(f){if(c.newsletterAction)f.action=c.newsletterAction;else f.addEventListener('submit',e=>{e.preventDefault();window.location.href='mailto:'+c.contactEmail+'?subject=Add me to Delaware Beach Finds&body=Please add this email to the Delaware Beach Finds list: '+encodeURIComponent(f.querySelector('input[type=email]').value)})}

 /* ---------------------------------------------------------------
    Data-driven sections. Each mount point fetches its own JSON file
    from /data/ and renders itself. Editing the JSON updates the
    live site — no HTML or layout changes required.
    --------------------------------------------------------------- */
 function dataUrl(name){
   // works whether the page lives at the site root or one folder deep (towns/, stories/)
   const depth = document.body.getAttribute('data-depth') || '0';
   const prefix = depth === '1' ? '../' : '';
   return prefix + 'data/' + name;
 }
 function esc(s){return (s||'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
 function sceneImg(scene, alt){
   const depth = document.body.getAttribute('data-depth') || '0';
   const prefix = depth === '1' ? '../' : '';
   const file = /\.(svg|jpe?g|png|webp)$/i.test(scene) ? scene : scene + '.svg';
      return `<img src="${prefix}assets/images/scenes/${esc(file)}" alt="${esc(alt||'')}" loading="lazy">`;
 }
 function fetchJson(name){
   return fetch(dataUrl(name)).then(r=>{ if(!r.ok) throw new Error('missing '+name); return r.json(); });
 }

 // Feature story (hero)
 const featureMount = document.querySelector('[data-mount="feature-story"]');
 if(featureMount){
   fetchJson('feature-story.json').then(d=>{
     featureMount.innerHTML = `
       <div class="scene">${sceneImg(d.scene, d.headline)}</div>
       <div class="container feature-inner">
         <div class="kicker">${esc(d.kicker)}</div>
         <h1>${esc(d.headline)}</h1>
         <p class="lede">${esc(d.teaser)}</p>
         <a class="link-arrow" href="${esc(d.link)}" style="color:#fff;font-size:1.05rem">${esc(d.linkText||'Read Story')} →</a>
       </div>`;
   }).catch(()=>{});
 }

 // Weekend calendar
 const weekendMount = document.querySelector('[data-mount="weekend"]');
 if(weekendMount){
   const limit = parseInt(weekendMount.getAttribute('data-limit')||'6',10);
   fetchJson('weekend.json').then(d=>{
     const updated = d.updated ? new Date(d.updated + 'T00:00:00') : null;
     const staleDays = updated ? Math.floor((Date.now() - updated.getTime()) / 86400000) : 0;
     if(updated && staleDays > 10){
       weekendMount.innerHTML = `<div class="calendar-stale"><p class="muted" style="margin:0">This week's lineup is being refreshed — check back soon, or see the <a href="events.html">Events page</a> for what's recurring all summer.</p></div>`;
       return;
     }
     const days = (d.days||[]).slice(0, limit);
     weekendMount.innerHTML = days.map((day,i)=>`
       <div class="calendar-day${i===0?' is-today':''}">
         <div class="day-label">${esc(day.label)}</div>
         <div class="day-date muted">${esc(day.date)}</div>
         <h4>${esc(day.title)}</h4>
         <p class="muted">${esc(day.description)}</p>
       </div>`).join('');
   }).catch(()=>{});
 }

 // Hidden gem
 const gemMount = document.querySelector('[data-mount="hidden-gem"]');
 if(gemMount){
   fetchJson('hidden-gems.json').then(list=>{
     const gem = list.find(g=>g.current) || list[0];
     if(!gem) return;
     gemMount.innerHTML = `
       <div class="gem-photo"><div class="scene">${sceneImg(gem.scene, gem.name)}</div></div>
       <div class="gem-copy">
         <div class="kicker">${esc(gem.kicker||'Hidden Gem of the Week')}</div>
         <h2>${esc(gem.name)}</h2>
         <p class="muted small">${esc(gem.location)}</p>
         ${(gem.body||[]).map(p=>`<p>${esc(p)}</p>`).join('')}
         <p class="signoff">${esc(gem.signoff)}</p>
       </div>`;
   }).catch(()=>{});
 }

 // Instagram
 const igMount = document.querySelector('[data-mount="instagram"]');
 if(igMount){
   fetchJson('instagram.json').then(d=>{
     if(d.permalink){
       igMount.innerHTML = `<blockquote class="instagram-media" data-instgrm-permalink="${esc(d.permalink)}" data-instgrm-version="14" style="margin:0"></blockquote>`;
       const s = document.createElement('script');
       s.async = true; s.src = 'https://www.instagram.com/embed.js';
       document.body.appendChild(s);
     } else {
       const igHref = withUtm(c.instagramUrl, 'instagram');
       igMount.innerHTML = `<a href="${esc(igHref)}" target="_blank" rel="noopener noreferrer" style="display:block;position:relative;height:100%;color:inherit"><div class="scene">${sceneImg(d.scene,'Latest on Instagram')}</div><div class="feature-inner" style="position:relative;z-index:2;padding:22px;color:#fff"><p style="margin:0">${esc(d.caption)}</p><p style="margin:8px 0 0;font-weight:700;font-size:.85rem">View @delawarebeachfinds &rarr;</p></div></a>`;
     }
   }).catch(()=>{});
 }

 // Community
 const communityMount = document.querySelector('[data-mount="community"]');
 if(communityMount){
   const mode = communityMount.getAttribute('data-mode') || 'compact';
   fetchJson('community.json').then(list=>{
     const byType = t => list.filter(x=>x.type===t);
     const photographer = byType('photographer').find(x=>x.featured) || byType('photographer')[0];
     const dog = byType('dog').find(x=>x.featured) || byType('dog')[0];
     const fishing = byType('fishing').find(x=>x.featured) || byType('fishing')[0];
     const sunrises = byType('sunrise');
     function mediaFor(entry){
       if(entry.image){
         const depth = document.body.getAttribute('data-depth') || '0';
         const prefix = depth === '1' ? '../' : '';
         return `<img src="${prefix}assets/images/community/${esc(entry.image)}" alt="${esc(entry.name||'')}" loading="lazy">`;
       }
       return sceneImg(entry.scene, entry.name);
     }
     function card(entry, label){
       if(!entry) return '';
       return `<article class="community-card">
         <div class="scene">${mediaFor(entry)}</div>
         <div class="card-copy">
           <div class="kicker">${esc(label)}</div>
           <h4>${esc(entry.name)}</h4>
           <p>${esc(entry.handle)} — ${esc(entry.caption)}</p>
         </div>
       </article>`;
     }
     const cards = [card(photographer,'Photographer of the Week'), card(dog,"Today's Beach Dog"), card(fishing,'Favorite Fishing Photo')].join('');
     const sunriseLimit = mode === 'full' ? sunrises.length : 6;
     const sunTiles = sunrises.slice(0, sunriseLimit).map(s=>`<div class="tile" title="${esc(s.name)} — ${esc(s.caption)}">${mediaFor(s)}</div>`).join('');
     communityMount.innerHTML = `
       <div class="community-grid">${cards}</div>
       <div class="section-head" style="margin-top:56px"><div><div class="kicker">Your Sunrise</div><h3 style="margin-top:6px">Tagged this week</h3></div></div>
       <div class="sunrise-grid">${sunTiles}</div>`;
   }).catch(()=>{});
 }

// Coastal Moments (video showcase)
 const videoMount = document.querySelector('[data-mount="coastal-moments"]');
 if(videoMount){
   fetchJson('coastal-moments.json').then(d=>{
     if(d.embedUrl){
       const isVideoFile = /\.(mp4|webm|mov)$/i.test(d.embedUrl);
       const player = isVideoFile
         ? `<video class="video-frame" controls playsinline preload="metadata" src="${esc(d.embedUrl)}"></video>`
         : `<div class="video-frame"><iframe src="${esc(d.embedUrl)}" title="Coastal Moments video" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen loading="lazy"></iframe></div>`;
       videoMount.innerHTML = `${player}<p class="video-caption">${esc(d.caption)}</p>`;
     } else {
       const igHref = withUtm(c.instagramUrl, 'coastal_moments');
       videoMount.innerHTML = `<a class="video-frame" href="${esc(igHref)}" target="_blank" rel="noopener noreferrer" style="display:block"><div class="scene">${sceneImg(d.scene,'Coastal Moments')}</div></a><p class="video-caption">${esc(d.caption)}</p>`;
     }
   }).catch(()=>{});
 }

  // Latest stories
 const storiesMount = document.querySelector('[data-mount="stories"]');
 if(storiesMount){
   const limit = parseInt(storiesMount.getAttribute('data-limit')||'0',10);
   fetchJson('stories.json').then(list=>{
     let items = list.slice();
     if(limit) items = items.filter(s=>!s.featured).slice(0, limit);
     storiesMount.innerHTML = items.map(s=>`
       <a class="story-card" href="stories/${esc(s.slug)}.html">
         <div class="story-art"><div class="scene">${sceneImg(s.scene, s.headline)}</div></div>
         <div class="kicker">${esc(s.kicker)}</div>
         <h3>${esc(s.headline)}</h3>
         <p>${esc(s.hook)}</p>
       </a>`).join('');
   }).catch(()=>{});
 }

 // Towns
 const townsMount = document.querySelector('[data-mount="towns"]');
 if(townsMount){
   fetchJson('towns.json').then(list=>{
     townsMount.innerHTML = list.map((t,i)=>`
       <a class="town-tile${i===0?' large':''}" href="towns/${esc(t.slug)}.html">
         <div class="scene">${sceneImg(t.tileScene, t.name)}</div>
         <div class="tile-copy"><div class="kicker">${esc(t.state)}</div><h3>${esc(t.name)}</h3></div>
       </a>`).join('');
   }).catch(()=>{});
 }

 // Shop
 const shopMount = document.querySelector('[data-mount="shop"]');
 if(shopMount){
   const limit = parseInt(shopMount.getAttribute('data-limit')||'0',10);
   fetchJson('shop.json').then(list=>{
     let items = list.slice();
     if(limit) items = items.slice(0, limit);
     shopMount.innerHTML = items.map(p=>{
       const storeAttr = p.store === 'etsy' ? 'data-etsy-link' : 'data-shopify-link data-fallback="shop.html"';
       const storeLabel = p.store === 'etsy' ? 'The Blue Hen Basement · Etsy' : 'Shopify';
       return `<a class="product-card" ${storeAttr} target="_blank" href="#">
         <div class="product-art"><div class="scene">${sceneImg(p.scene, p.name)}</div></div>
         <span class="store-tag">${storeLabel}</span>
         <h4>${esc(p.name)}</h4>
         <p>${esc(p.description)}</p>
         <span class="price-line">${esc(p.price)}</span>
       </a>`;
     }).join('');
     document.querySelectorAll('[data-etsy-link]').forEach(a=>a.href=withUtm(c.etsyUrl,'etsy_shop'));
     document.querySelectorAll('[data-shopify-link]').forEach(a=>{
       if(validShopify){a.href=withUtm(c.shopifyUrl,'shopify_store')}else{a.href=(a.dataset.fallback||'shop.html');}
     });
   }).catch(()=>{});
 }
})();
