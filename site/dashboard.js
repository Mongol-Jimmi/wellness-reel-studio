const ideasContainer = document.querySelector('#ideas');
const reelsContainer = document.querySelector('#reels');
const repository = 'Mongol-Jimmi/wellness-reel-studio';
const previewRelease = `https://api.github.com/repos/${repository}/releases/tags/preview-assets`;

function text(tag, value, className) {
  const element = document.createElement(tag);
  element.textContent = value;
  if (className) element.className = className;
  return element;
}

function safeUrl(value) {
  const url = new URL(value, window.location.href);
  if (url.protocol !== 'https:') throw new Error('Unsupported link protocol');
  return url.href;
}

function link(label, url) {
  const element = document.createElement('a');
  element.href = safeUrl(url);
  element.textContent = label;
  element.rel = 'noopener';
  return element;
}

function currentState(issue) {
  const stateLabel = issue.labels.find((label) => label.name.startsWith('state:'));
  return stateLabel ? stateLabel.name.slice(6).replaceAll('-', ' ') : 'proposed';
}

function ideaCard(issue) {
  const article = document.createElement('article');
  article.className = 'card idea-card';
  article.append(text('p', currentState(issue), 'status'));
  article.append(text('h3', issue.title.replace('[Topic Proposal] ', '')));
  article.append(text('p', `Issue #${issue.number}`, 'meta'));
  article.append(link('Open decision →', issue.html_url));
  return article;
}

function reelCard(reel) {
  const article = document.createElement('article');
  article.className = 'card';

  const video = document.createElement('video');
  video.controls = true;
  video.preload = 'metadata';
  video.playsInline = true;
  video.src = safeUrl(reel.video);
  if (reel.poster) video.poster = safeUrl(reel.poster);
  article.id = `reel-${reel.slug}`;
  article.append(video);
  article.append(text('h3', reel.title));
  article.append(text('p', `${reel.duration} · ${reel.resolution}`, 'meta'));
  article.append(text('p', `${reel.sourceIssue} · render ${reel.renderVersion}`, 'meta'));
  article.append(text('p', reel.status, 'status'));

  const links = document.createElement('p');
  for (const [label, url] of Object.entries(reel.links || {})) {
    links.append(link(label, url), ' ');
  }
  article.append(links);
  return article;
}

fetch(`https://api.github.com/repos/${repository}/issues?state=all&labels=topic-proposal&per_page=100`)
  .then((response) => {
    if (!response.ok) throw new Error('Could not load topic decisions');
    return response.json();
  })
  .then((issues) => {
    if (!issues.length) {
      ideasContainer.append(text('p', 'No topic proposals yet.', 'empty'));
      return;
    }
    issues
      .filter((issue) => !issue.pull_request)
      .sort((a, b) => a.number - b.number)
      .forEach((issue) => ideasContainer.append(ideaCard(issue)));
  })
  .catch(() => {
    const fallback = link('Open topic proposals on GitHub →', `https://github.com/${repository}/issues?q=label%3Atopic-proposal`);
    fallback.className = 'empty';
    ideasContainer.append(fallback);
  });

function fetchJson(url, optional = false) {
  return fetch(url).then((response) => {
    if (optional && response.status === 404) return [];
    if (!response.ok) throw new Error('Could not load previews');
    return response.json();
  });
}

function releasePreviews() {
  return fetchJson(previewRelease, true)
    .then((release) => {
      if (Array.isArray(release)) return [];
      const metadata = release.assets.filter((asset) => asset.name.endsWith('.preview.json'));
      return Promise.all(metadata.map((asset) => fetchJson(asset.browser_download_url)
        .then((preview) => ({ preview, asset }))));
    })
    .then((items) => items.map(({ preview, asset }) => {
      const base = asset.browser_download_url.slice(0, -asset.name.length);
      return {
        slug: preview.slug,
        title: preview.title,
        status: preview.status,
        duration: preview.duration,
        resolution: preview.resolution,
        renderVersion: preview.renderVersion,
        sourceIssue: `Issue #${preview.issueNumber}`,
        video: `${base}${preview.videoFile}`,
        poster: `${base}${preview.posterFile}`,
        links: {
          Issue: `https://github.com/${repository}/issues/${preview.issueNumber}`,
          Captions: `${base}${preview.captionsFile}`,
          'Reel Spec': `https://github.com/${repository}/blob/main/${preview.specPath}`,
          Evidence: preview.sources[0],
        },
      };
    }));
}

Promise.all([fetchJson('reels.json'), releasePreviews()])
  .then(([staticReels, generatedReels]) => [...staticReels, ...generatedReels])
  .then((reels) => {
    if (!reels.length) {
      reelsContainer.append(text('p', 'No rendered previews yet.', 'empty'));
      return;
    }
    reels.forEach((reel) => reelsContainer.append(reelCard(reel)));
    const requested = new URLSearchParams(window.location.search).get('reel');
    if (requested && /^[a-z0-9-]+$/.test(requested)) {
      document.querySelector(`#reel-${requested}`)?.scrollIntoView();
    }
  })
  .catch((error) => reelsContainer.append(text('p', error.message, 'empty')));
