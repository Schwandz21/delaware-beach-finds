(function(){
 const c=window.DBF_CONFIG||{};
 function withUtm(url, campaign, content){
   try{const u=new URL(url);u.searchParams.set('utm_source','delawarebeachfinds');u.searchParams.set('utm_medium','website');u.searchParams.set('utm_campaign',campaign||'sitewide');if(content)u.searchParams.set('utm_content',content);return u.toString()}catch(e){return url}
 }
 document.querySelectorAll('[data-instagram-link]').forEach(a=>a.href=withUtm(c.instagramUrl,'instagram'));
 document.querySelectorAll('[data-etsy-link]').forEach(a=>a.href=withUtm(c.etsyUrl,'etsy_shop'));
 document.querySelectorAll('[data-contact-email]').forEach(a=>{a.href='mailto:'+c.contactEmail;a.textContent=c.contactEmail});
 document.querySelectorAll('[data-year]').forEach(el=>el.textContent=new Date().getFullYear());
 const t=document.querySelector('.menu-toggle'),n=document.querySelector('.nav-links');if(t&&n)t.addEventListener('click',()=>{const o=n.classList.toggle('open');t.setAttribute('aria-expanded',o?'true':'false')});
 document.querySelectorAll('a[target="_blank"]').forEach(a=>a.setAttribute('rel','noopener noreferrer'));
 if(c.googleAnalyticsId){const g=document.createElement('script');g.async=true;g.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(c.googleAnalyticsId);document.head.appendChild(g);window.dataLayer=window.dataLayer||[];window.gtag=function(){dataLayer.push(arguments)};gtag('js',new Date());gtag('config',c.googleAnalyticsId);}
 document.addEventListener('click',function(e){var a=e.target.closest('[data-etsy-link]');if(!a||!window.gtag)return;var isProduct=a.hasAttribute('data-product');var pid=(a.href.match(/listing\/(\d+)/)||[])[1];gtag('event',isProduct?'etsy_product_click':'etsy_collection_click',{destination:a.href,product_name:a.dataset.product||undefined,product_id:pid||undefined,source_page:location.pathname,link_placement:a.dataset.placement||(a.closest('.footer')?'footer':a.closest('.shop-grid')?'shop_grid':a.closest('.nav-links')?'nav':a.closest('.cta-strip')?'hero_cta':'body'),content_category:'shop'});});
document.addEventListener('click',function(e){var a=e.target.closest('[data-instagram-link]');if(!a||!window.gtag)return;gtag('event','instagram_click',{destination:a.href,source_page:location.pathname,link_placement:a.dataset.placement||(a.closest('.footer')?'footer':a.closest('.nav-links')?'nav':a.closest('[data-mount="instagram"]')?'instagram_feature':'body'),content_category:'social'});});
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
   if(/^https?:\/\//i.test(scene)) return `<img src="${esc(scene)}" alt="${esc(alt||'')}" loading="lazy" decoding="async">`;
  const file = /\.(svg|jpe?g|png|webp)$/i.test(scene) ? scene : scene + '.svg';
  return `<img src="${prefix}assets/images/scenes/${esc(file)}" alt="${esc(alt||'')}" loading="lazy" decoding="async">`;
 }
 const CAT_LABELS={coast:'Delaware Coast',history:'The First State Story',people:'People of Delaware','field-guide':'Delaware Field Guide',community:'Through the Local Lens'};
 function fetchJson(name){
   return fetch(dataUrl(name)).then(r=>{ if(!r.ok) throw new Error('missing '+name); return r.json(); });
 }

 const featureMount = document.querySelector('[data-mount="feature-story"]');
 if(featureMount){
  Promise.all([fetchJson('feature-story.json'), fetchJson('stories.json')]).then(([f,stories])=>{
   const d = stories.find(s=>s.slug===f.slug);
   if(!d) return;
   featureMount.innerHTML = `
   <div class="scene">${sceneImg(d.scene, d.headline)}</div>
   <div class="container feature-inner">
   <div class="kicker">${esc(d.kicker)}</div>
    <div class="feature-meta" style="color:rgba(255,255,255,.78);font-size:.85rem;letter-spacing:.03em;margin:.25em 0 .5em;text-transform:uppercase">${esc(CAT_LABELS[d.category]||d.category)}${d.readTime? " · "+esc(d.readTime):""}</div>
   <h1>${esc(d.headline)}</h1>
   <p class="lede">${esc(d.hook)}</p>
   <div class="feature-cta-row" style="display:flex;flex-wrap:wrap;align-items:center;gap:10px 28px;margin-top:2px"><a class="link-arrow" href="${esc('stories/'+d.slug+'.html')}" style="color:#fff;font-size:1.05rem">Read the story &rarr;</a>
    <a class="link-arrow" href="stories/index.html" style="color:rgba(255,255,255,.85);font-size:.95rem">Explore All Stories &rarr;</a></div>
   </div>`;
  }).catch(()=>{});
 }

 // Weekend / event calendar — reads data/events.json, filters by real dates
 function todayEasternISO(){
   try{ return new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York'}).format(new Date()); }
   catch(e){ return new Date().toISOString().slice(0,10); }
 }
 const STATUS_BADGE = {tentative:'Tentative',cancelled:'Cancelled',postponed:'Postponed','sold-out':'Sold Out'};
 const weekendMount = document.querySelector('[data-mount="weekend"]');
 if(weekendMount){
   const limit = parseInt(weekendMount.getAttribute('data-limit')||'6',10);
   fetchJson('events.json').then(d=>{
     const today = todayEasternISO();
     const verifiedAt = d.verifiedAt || null;
     const policyDays = d.freshnessPolicyDays || 7;
     const staleDays = verifiedAt ? Math.floor((Date.now() - new Date(verifiedAt+'T00:00:00').getTime()) / 86400000) : null;
     const staleDataset = verifiedAt===null || staleDays > policyDays;
     const upcoming = (d.events||[])
       .filter(e => e.endDate && e.endDate >= today)
       .sort((a,b) => (a.startDate||'').localeCompare(b.startDate||''));
     if(staleDataset || !upcoming.length){
       weekendMount.innerHTML = `<div class="calendar-stale"><p class="muted" style="margin:0">Fresh events are being verified — check back shortly for this week's confirmed picks, or explore our <a href="guides.html">current local guides</a> in the meantime.</p></div>`;
       return;
     }
     const items = upcoming.slice(0, limit);
     weekendMount.innerHTML = items.map((e,i)=>{
       const badge = STATUS_BADGE[e.status];
       let weekday = '';
       try{ weekday = new Intl.DateTimeFormat('en-US',{weekday:'long',timeZone:'America/New_York'}).format(new Date(e.startDate+'T12:00:00Z')); }catch(err){}
       return `
       <div class="calendar-day${i===0?' is-today':''}">
         <div class="day-label">${esc(weekday)}${badge?` &middot; <span class="event-status-badge">${esc(badge)}</span>`:''}</div>
         <div class="day-date muted">${esc(e.displayDate||e.startDate||'')}${e.town?` &middot; ${esc(e.town)}`:''}</div>
         <h4>${esc(e.title)}</h4>
         <p class="muted">${esc(e.description||'')}</p>
       </div>`;
     }).join('');
   }).catch(()=>{
     weekendMount.innerHTML = `<div class="calendar-stale"><p class="muted" style="margin:0">Fresh events are being verified — check back shortly, or explore our <a href="guides.html">current local guides</a> in the meantime.</p></div>`;
   });
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
         const real = list.filter(x=>!x.placeholder);
         const byType = t => real.filter(x=>x.type===t);
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
         if(!photographer && !dog && !fishing && !sunrises.length){
                communityMount.innerHTML = `<div class="community-cta" style="text-align:center;padding:48px 24px;border:1px solid #e2ddd3;border-radius:12px">
                        <div class="kicker">Submissions Opening Soon</div>
                                <h3 style="margin-top:8px">Be the first to show up here.</h3>
                                        <p class="muted" style="max-width:480px;margin:10px auto 0">Tag <strong>@delawarebeachfinds</strong> with your best shot of the coast, your beach dog, your catch of the day, or your sunrise. The first Photographer of the Week, Beach Dog and First State Frame are picked from real reader tags.</p>
                                              </div>`;
                return;
         }
         communityMount.innerHTML = `
               <div class="community-grid">${cards}</div>
                     ${sunTiles ? `<div class="section-head" style="margin-top:56px"><div><div class="kicker">Your Sunrise</div><h3 style="margin-top:6px">Tagged this week</h3></div></div><div class="sunrise-grid">${sunTiles}</div>` : ''}`;
    }).catch(()=>{});
 }

 // First State Frame of the Week
 const frameMount = document.querySelector('[data-mount="frame-of-week"]');
 if(frameMount){
    fetchJson('frame-of-the-week.json').then(d=>{
         const current = d.current;
         const hallOfFame = d.hallOfFame || [];
         if(!current){
                frameMount.innerHTML = `<div class="community-cta" style="text-align:center;padding:48px 24px;border:1px solid #e2ddd3;border-radius:12px">
                        <div class="kicker">First State Frame of the Week</div>
                                <h3 style="margin-top:8px">Submissions opening soon.</h3>
                                        <p class="muted" style="max-width:480px;margin:10px auto 0">Every week we will pick one reader photo as the First State Frame &mdash; full credit, a feature here, and a spot in the Hall of Fame. Tag @delawarebeachfinds to be considered.</p>
                                              </div>`;
                return;
         }
         function frameCard(entry, isCurrent){
                return `<article class="community-card">
                        <div class="scene">${sceneImg(entry.scene, entry.name)}</div>
                                <div class="card-copy">
                                          <div class="kicker">${isCurrent ? 'First State Frame of the Week' : esc(entry.week||'')}</div>
                                                    <h4>${esc(entry.name)}</h4>
                                                              <p>${esc(entry.handle)} &mdash; ${esc(entry.caption)}</p>
                                                                      </div>
                                                                            </article>`;
         }
         const hofTiles = hallOfFame.map(e=>frameCard(e,false)).join('');
         frameMount.innerHTML = `
               <div class="community-grid">${frameCard(current,true)}</div>
                     ${hofTiles ? `<div class="section-head" style="margin-top:56px"><div><div class="kicker">Hall of Fame</div><h3 style="margin-top:6px">Past First State Frames</h3></div></div><div class="community-grid">${hofTiles}</div>` : ''}`;
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
  const categoryFilter = storiesMount.getAttribute('data-category');
  const seriesFilter = storiesMount.getAttribute('data-series');
  const storiesDepth = document.body.getAttribute('data-depth') || '0';
  const storiesPrefix = storiesDepth === '1' ? '' : 'stories/';
  fetchJson('stories.json').then(list=>{
    let items = list.slice();
    if(categoryFilter) items = items.filter(s=>s.category===categoryFilter);
    if(seriesFilter) items = items.filter(s=>s.series===seriesFilter);
    if(limit) items = items.filter(s=>!s.featured).slice(0, limit);
    if(seriesFilter) items.sort((a,b)=>(a.seriesInstallment||0)-(b.seriesInstallment||0));
    if(!items.length){
      storiesMount.innerHTML = `<div class="community-cta" style="text-align:center;padding:48px 24px;border:1px solid #e2ddd3;border-radius:12px">
        <div class="kicker">More on the way</div>
        <h3 style="margin-top:8px">Nothing published here yet.</h3>
        <p class="muted" style="max-width:480px;margin:10px auto 0">Check back soon &mdash; new stories are in the works.</p>
      </div>`;
      return;
    }
    storiesMount.innerHTML = items.map(s=>`
      <a class="story-card" href="${storiesPrefix}${esc(s.slug)}.html">
        <div class="story-art"><div class="scene">${sceneImg(s.scene, s.headline)}</div></div>
        <div class="kicker">${esc(s.kicker)}</div>
         <div class="card-meta muted" style="font-size:.75rem;letter-spacing:.02em;margin:.15em 0">${esc(CAT_LABELS[s.category]||s.category)}${s.readTime? " · "+esc(s.readTime):""}</div>
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
          const storeLabel = p.storeLabel || 'DelawareBeachFinds · Etsy';
          const shopBase = c.delawareBeachFindsUrl || c.etsyUrl;
      const productHref = withUtm(p.url||shopBase, 'etsy_shop', p.shop||'dbf');
      return `<a class="product-card" data-etsy-link data-product="${esc(p.name)}" target="_blank" href="${esc(productHref)}">
         <div class="product-art"><div class="scene">${sceneImg(p.scene, p.name)}</div></div>
         <span class="store-tag">${storeLabel}</span>
         <h4>${esc(p.name)}</h4>
         <p>${esc(p.description)}</p>
         <span class="price-line">${esc(p.price)}</span>
       </a>`;
     }).join('');
         if(window.gtag) gtag('event','view_shop',{source_page:location.pathname,product_count:list.length});
   }).catch(()=>{});
 }

// Shop the Story (used on article pages: <div data-mount="shop-the-story" data-story="story-slug"></div>)
document.querySelectorAll('[data-mount="shop-the-story"]').forEach(mount=>{
  const storySlug = mount.getAttribute('data-story');
  if(!storySlug) return;
  Promise.all([fetchJson('stories.json'), fetchJson('shop.json')]).then(([stories, shop])=>{
    const story = stories.find(s=>s.slug===storySlug);
    const ids = (story && story.etsyProductIds) || [];
    if(!ids.length){ mount.remove(); return; }
    const products = shop.filter(p=>{
      const m = (p.url||'').match(/listing\/(\d+)/);
      return m && ids.includes(m[1]);
    });
    if(!products.length){ mount.remove(); return; }
    mount.innerHTML = `<div class="section-head"><div><div class="kicker">Shop the Story</div><h3 style="margin-top:6px">Bring a piece of this one home</h3></div></div>
      <div class="shop-grid">${products.map(p=>{
        const storeLabel = p.storeLabel || 'DelawareBeachFinds \u00b7 Etsy';
        return `<a class="product-card" data-etsy-link data-product="${esc(p.name)}" target="_blank" href="${esc(p.url)}">
          <div class="product-art"><div class="scene">${sceneImg(p.scene, p.name)}</div></div>
          <span class="store-tag">${esc(storeLabel)}</span>
          <h4>${esc(p.name)}</h4>
          <span class="price-line">${esc(p.price)}</span>
        </a>`;
      }).join('')}</div>`;
  }).catch(()=>{});
});

// Guides (reusable guide-card grid: data-mount="guides" data-limit="0")
const guidesMount = document.querySelector('[data-mount="guides"]');
if(guidesMount){
  const guideLimit = parseInt(guidesMount.getAttribute('data-limit')||'0',10);
  const guidesDepth = document.body.getAttribute('data-depth') || '0';
  const guidesPrefix = guidesDepth === '1' ? '../' : '';
  fetchJson('guides.json').then(list=>{
    let items = list.slice();
    if(guideLimit) items = items.slice(0, guideLimit);
    const todayStr = todayEasternISO();
    guidesMount.innerHTML = items.map(g=>{
      const isSoon = g.status !== 'published';
      let soonLabel = 'Coming Soon', soonMeta = 'In the works';
      if(isSoon){
        const interval = g.reviewIntervalDays || 14;
        const reviewed = g.lastReviewed || null;
        const daysSince = reviewed ? Math.floor((new Date(todayStr) - new Date(reviewed)) / 86400000) : null;
        if(daysSince===null || daysSince > interval){ soonLabel = 'On Our List'; soonMeta = 'Under review — check back later'; }
      }
      const inner = `
        <div class="guide-hub-art"><span class="guide-hub-badge">${isSoon?soonLabel:esc(g.kicker)}</span><div class="scene">${sceneImg(g.scene, g.title)}</div></div>
        <div class="guide-hub-body">
          <h3>${esc(g.title)}</h3>
          <p>${esc(g.dek)}</p>
          <div class="guide-hub-meta">${isSoon?soonMeta:(esc(g.meta||'')+' &rarr;')}</div>
        </div>`;
      return isSoon
        ? `<div class="guide-hub-card is-soon">${inner}</div>`
        : `<a class="guide-hub-card" href="${guidesPrefix}${esc(g.href)}">${inner}</a>`;
    }).join('');
  }).catch(()=>{});
}

// Series hero (data-mount="series-hero" data-series="[slug]") — overwrites static fallback content already in the mount
document.querySelectorAll('[data-mount="series-hero"]').forEach(mount=>{
const seriesSlug = mount.getAttribute('data-series');
if(!seriesSlug) return;
fetchJson('series.json').then(list=>{
const s = list.find(x=>x.slug===seriesSlug);
if(!s) return;
mount.innerHTML = `<div class="kicker">A Delaware Beach Finds Series</div><h1>${esc(s.title)}</h1><p class="lede">${esc(s.description)}</p>`;
}).catch(()=>{});
});

// Series prev/next navigation (data-mount="series-nav" data-story="[slug]")
document.querySelectorAll('[data-mount="series-nav"]').forEach(mount=>{
const slug = mount.getAttribute('data-story');
if(!slug) return;
fetchJson('stories.json').then(list=>{
const story = list.find(s=>s.slug===slug);
if(!story || !story.series){ mount.remove(); return; }
const items = list.filter(s=>s.series===story.series && s.status==='published').sort((a,b)=>(a.seriesInstallment||0)-(b.seriesInstallment||0));
const idx = items.findIndex(s=>s.slug===slug);
const prev = idx>0 ? items[idx-1] : null;
const next = (idx>=0 && idx<items.length-1) ? items[idx+1] : null;
if(!prev && !next){ mount.remove(); return; }
mount.innerHTML = `<div class="series-nav">
${prev ? `<a class="series-nav-link prev" href="${esc(prev.slug)}.html"><span class="muted small">&larr; Installment ${prev.seriesInstallment}</span><br>${esc(prev.headline)}</a>` : '<span></span>'}
${next ? `<a class="series-nav-link next" href="${esc(next.slug)}.html"><span class="muted small">Installment ${next.seriesInstallment} &rarr;</span><br>${esc(next.headline)}</a>` : '<span></span>'}
</div>`;
}).catch(()=>{ mount.remove(); });
});

// Related stories (data-mount="related-stories" data-story="[slug]" data-limit="3") — replaces the static "Keep reading" list already in the mount
document.querySelectorAll('[data-mount="related-stories"]').forEach(mount=>{
const slug = mount.getAttribute('data-story');
const relLimit = parseInt(mount.getAttribute('data-limit')||'3',10);
if(!slug) return;
const relDepth = document.body.getAttribute('data-depth') || '0';
const relPrefix = relDepth === '1' ? '' : 'stories/';
fetchJson('stories.json').then(list=>{
const story = list.find(s=>s.slug===slug);
if(!story) return;
let related = list.filter(s=>s.slug!==slug && s.status==='published' && ((story.series && s.series===story.series) || s.category===story.category));
related.sort((a,b)=>{
const aSame = story.series && a.series===story.series ? 0 : 1;
const bSame = story.series && b.series===story.series ? 0 : 1;
return aSame - bSame;
});
related = related.slice(0, relLimit);
if(!related.length) return;
mount.innerHTML = `<h4>Keep reading</h4><ul>${related.map(r=>`<li><a href="${relPrefix}${esc(r.slug)}.html">${esc(r.headline)}</a></li>`).join('')}</ul><hr class="rule" style="margin:16px 0"><a class="link-arrow" href="${relPrefix}index.html">All stories &rarr;</a>`;
}).catch(()=>{});
});

// The Edit (content-gated curation: data-mount="dbf-edit", hides itself and its
// department-nav panel unless data/dbf-edit.json has enough valid real entries)
const editMount = document.querySelector('[data-mount="dbf-edit"]');
if(editMount){
  const editSection = editMount.closest('section');
  const editNavPanel = document.querySelector('[data-dept-panel="the-edit"]');
  fetchJson('dbf-edit.json').then(d=>{
    const minCount = d.minPublishCount || 3;
    const valid = (d.entries||[]).filter(e=>e.title && e.image && e.url && e.description);
    if(valid.length < minCount){
      if(editSection) editSection.classList.add('is-hidden');
      if(editNavPanel) editNavPanel.classList.add('is-hidden');
      return;
    }
    editMount.innerHTML = valid.map(e=>`
      <a class="edit-card" href="${esc(e.url)}" target="_blank" rel="noopener noreferrer" data-etsy-link data-product="${esc(e.title)}" data-placement="the_edit">
        <div class="edit-art"><img src="${esc(e.image)}" alt="${esc(e.title)}" loading="lazy" decoding="async"></div>
        <div class="edit-body">
          <span class="edit-tag">${esc(e.tag||'')}</span>
          <h3>${esc(e.title)}</h3>
          <p>${esc(e.editorialNote || e.description)}</p>
          <span class="price-line">${esc(e.price||'')}</span>
        </div>
      </a>`).join('');
    if(editNavPanel) editNavPanel.classList.remove('is-hidden');
  }).catch(()=>{
    if(editSection) editSection.classList.add('is-hidden');
    if(editNavPanel) editNavPanel.classList.add('is-hidden');
  });
}

// Restrained scroll-reveal for .reveal elements — no-op visually under prefers-reduced-motion
// (CSS already neutralizes the effect there; this just avoids the redundant observer work)
const prefersReducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const revealEls = document.querySelectorAll('.reveal');
if(revealEls.length && !prefersReducedMotion && 'IntersectionObserver' in window){
  const io = new IntersectionObserver((entries)=>{
    entries.forEach(entry=>{
      if(entry.isIntersecting){
        entry.target.classList.add('is-visible');
        io.unobserve(entry.target);
      }
    });
  }, {threshold:0.12, rootMargin:'0px 0px -40px 0px'});
  revealEls.forEach(el=>io.observe(el));
} else {
  revealEls.forEach(el=>el.classList.add('is-visible'));
}

})();
