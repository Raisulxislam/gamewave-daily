# GameWave

Gaming news, leaks, reviews & updates — surf the game wave.

GameWave auto-scans the web twice a day, grabs verified imagery, and publishes
an IGN/PC Gamer-style magazine site (hero slider + section grids) with
X/Twitter-style article pages and GitHub-powered comments.

## Stack

- **Hugo** static site (`themes/gamewave`, hand-written, no external deps)
- **Python 3** scanner (`scripts/scan_news.py`) — RSS → verified images → posts
- **Shell** pipeline (`scripts/publish.sh`) — scan → build → git push
- **Vercel** hosting (import this repo)

## Layout

```
hugo.toml          site config
content/posts/     generated articles (markdown)
themes/gamewave/   custom theme (templates + style.css + app.js)
scripts/           scanner + publish pipeline
```

## Publish pipeline

```sh
scripts/publish.sh
```

Steps: fetch RSS -> download verified images -> draft posts -> hugo build -> commit/push.
Scheduled twice daily via cron (`crond`).

## Comments

Comments use [utterances](https://utteranc.es) on GitHub issues. Keep this repo
public for comments and Vercel deployment to work.

## License

Content produced automatically from public RSS feeds; links to original sources included.