# Delaware Beach Finds — GitHub Pages Version 1

This is a dependency-free static website built for `delawarebeachfinds.com`.

## 1. Before you upload

### Add the exact hero image
The image attachment did not arrive in the build conversation, so the site includes a polished fallback. To use the exact hero photo:

1. Name the image `hero.jpg`.
2. Put it in `assets/images/hero.jpg`.
3. Do not change the HTML or CSS. The existing background stack automatically uses `hero.jpg` before the fallback.
4. Recommended crop: 16:9 or wider, at least 1920 px wide, optimized below roughly 500 KB if possible.

### Connect Shopify
Open `assets/js/config.js` and replace:

`https://YOUR-SHOPIFY-STORE.myshopify.com`

with the real public Shopify store URL. Every Shopify button sitewide updates from that one setting.

### Confirm existing links
- Etsy is prefilled as `https://www.etsy.com/shop/TheBlueHenBasement`
- Instagram is prefilled as `https://www.instagram.com/delawarebeachfinds/`
- Contact email is prefilled as `michael@rentdelawarebeaches.com`

## 2. Upload to GitHub

1. Create a new repository, for example `delaware-beach-finds`.
2. Upload the **contents** of this folder to the repository root. Do not upload the outer folder as a single nested directory.
3. Commit to the `main` branch.
4. Open **Settings → Pages**.
5. Under **Build and deployment**, choose **Deploy from a branch**.
6. Select `main` and `/(root)`, then save.

## 3. Attach delawarebeachfinds.com

1. In the repository, open **Settings → Pages**.
2. Enter `delawarebeachfinds.com` under **Custom domain** and save.
3. At the DNS provider, use the current GitHub Pages apex A records:
   - `185.199.108.153`
   - `185.199.109.153`
   - `185.199.110.153`
   - `185.199.111.153`
4. Add `www` as a CNAME pointing to `YOUR-GITHUB-USERNAME.github.io`.
5. After DNS resolves, enable **Enforce HTTPS** in GitHub Pages settings.
6. Avoid wildcard DNS records.

GitHub notes DNS can take up to 24 hours to propagate. Confirm all values against GitHub's current custom-domain documentation before changing DNS.

## 4. Optional launch settings

Open `assets/js/config.js`:

- `googleAnalyticsId`: add a GA4 Measurement ID such as `G-XXXXXXXXXX`.
- `newsletterAction`: add a Mailchimp, ConvertKit or Formspree form endpoint. When blank, the newsletter form opens an email draft.
- `contactEmail`: change the sitewide contact address in one place.

## 5. SEO work already included

- Unique titles and descriptions
- Canonical URLs
- Open Graph and Twitter metadata
- Organization, Website and BlogPosting structured data
- `sitemap.xml`
- `robots.txt`
- `feed.xml`
- Internal links between guides and store pages
- Human-readable URLs
- Source and verification links in travel articles
- Mobile-first responsive design
- Fast vanilla CSS and JavaScript
- Accessible navigation, skip link and semantic structure

## 6. Recommended first edits

1. Add the exact hero image.
2. Add the real Shopify URL.
3. Replace generic Shopify product language with the first 3–5 live products.
4. Add real Instagram post URLs or approved images to the media page.
5. Review every travel article for personal voice and firsthand additions.
6. Submit `https://delawarebeachfinds.com/sitemap.xml` to Google Search Console.
7. Add GA4 after confirming the privacy and cookie approach you want.

## Important
Travel rules, business hours, park access, prices and transportation schedules change. The articles intentionally direct readers to official sources and should be reviewed periodically.
