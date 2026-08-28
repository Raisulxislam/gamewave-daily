# GameWave

Gaming news, leaks, reviews & updates — surf the game wave.

GameWave auto-scans the web twice a day, grabs verified imagery, and publishes
an IGN/PC Gamer-style magazine site (hero slider + section grids) with
X/Twitter-style article pages and GitHub-powered comments. Every article is
rewritten from scratch in GameWave's own house style (no source text, no source
links) and every article ships with an optional বাংলা (Bangla) translation
toggle.

## Stack

- **Hugo** static site (`themes/gamewave`, hand-written, no external deps)
- **Python 3** scanner (`scripts/scan_news.py`) — RSS → verified images → drafts
- **Python 3** rewriter (`scripts/rewrite.py`) — opencode headless → original
  prose + Bangla translation per post
- **Shell** pipeline (`scripts/publish.sh`) — scan → rewrite → build → git push
- **Vercel** hosting (import this repo)

## Layout

```
hugo.toml          site config
content/posts/     generated articles (markdown + content_bn front matter)
themes/gamewave/   custom theme (templates + style.css + app.js)
scripts/           scanner + rewriter + publish pipeline
```

## Publish pipeline

```sh
scripts/publish.sh
```

Steps: fetch RSS -> download verified images -> draft posts -> opencode rewrite
(original prose + বাংলা) -> hugo build -> commit/push. Scheduled twice daily via
cron (`crond`).

## Comments

Comments use [utterances](https://utteranc.es) on GitHub issues. Keep this repo
public for comments and Vercel deployment to work.

## License

Content is rewritten from public RSS feeds in GameWave's own original prose.