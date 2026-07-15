(function(){
 const c=window.DBF_CONFIG||{};
 const validShopify=c.shopifyUrl && !c.shopifyUrl.includes('YOUR-SHOPIFY');
 function withUtm(url, campaign){
   try{const u=new URL(url);u.searchParams.set('utm_source','delawarebeachfinds');u.searchParams.set('utm_medium','website');u.searchParams.set('utm_campaign',campaign||'sitewide');return u.toString()}catch(e){return url}
 }
 document.querySelectorAll('[data-instagram-link]').forEach(a=>a.href=withUtm(c.instagramUrl,'instagram'));
 document.querySelectorAll('[data-etsy-link]').forEach(a=>a.href=withUtm(c.etsyUrl,'etsy_shop'));
 document.querySelectorAll('[data-shopify-link]').forEach(a=>{
   if(validShopify){a.href=withUtm(c.shopifyUrl,'shopify_store')}else{a.href=(a.dataset.fallback||'shop.html#connect-shopify');a.title='Add your Shopify URL in assets/js/config.js before launch';}
 });
 document.querySelectorAll('[data-contact-email]').forEach(a=>{a.href='mailto:'+c.contactEmail;a.textContent=c.contactEmail});
 document.querySelectorAll('[data-year]').forEach(el=>el.textContent=new Date().getFullYear());
 const t=document.querySelector('.menu-toggle'),n=document.querySelector('.nav-links');if(t&&n)t.addEventListener('click',()=>{const o=n.classList.toggle('open');t.setAttribute('aria-expanded',o?'true':'false')});
 document.querySelectorAll('a[target="_blank"]').forEach(a=>a.setAttribute('rel','noopener noreferrer'));
 const s=document.querySelector('[data-guide-search]');if(s){s.addEventListener('input',()=>{const q=s.value.toLowerCase().trim();document.querySelectorAll('[data-guide-card]').forEach(card=>card.classList.toggle('hidden',!card.textContent.toLowerCase().includes(q)))})}
 if(c.googleAnalyticsId){const g=document.createElement('script');g.async=true;g.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(c.googleAnalyticsId);document.head.appendChild(g);window.dataLayer=window.dataLayer||[];window.gtag=function(){dataLayer.push(arguments)};gtag('js',new Date());gtag('config',c.googleAnalyticsId);}
 const f=document.querySelector('[data-newsletter-form]');if(f){if(c.newsletterAction)f.action=c.newsletterAction;else f.addEventListener('submit',e=>{e.preventDefault();window.location.href='mailto:'+c.contactEmail+'?subject=Add me to Delaware Beach Finds&body=Please add this email to the Delaware Beach Finds list: '+encodeURIComponent(f.querySelector('input[type=email]').value)})}
})();
