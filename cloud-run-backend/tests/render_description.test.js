// Run with: node cloud-run-backend/tests/render_description.test.js
// The episode page renders the stored Markdown (never rewrites it): structure, linked references, the Further reading pointer, no hashtags.
// Fixtures are real episodes from the public API (2026-10-14): ever-math-260010 (new format) and three older ones.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { renderDescriptionHtml, referenceUrl, referenceHtml } = require('../../api/_lib/render-description');

const root = path.join(__dirname, '..', '..');
const fx = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'episodes_render.json'), 'utf8')).episodes;
const count = (s, re) => (s.match(re) || []).length;

// ---------------------------------------------------------------- ever-math-260010
{
  const html = renderDescriptionHtml(fx['ever-math-260010'].description_markdown, { hasFurtherReading: true });
  // 1. references: one link each, arXiv abs URL with the version when there is one
  const refs = html.slice(html.indexOf('<ul class="references">'), html.indexOf('</ul>', html.indexOf('<ul class="references">')));
  assert.strictEqual(count(refs, /<li>/g), 5);
  for (const url of ['https://arxiv.org/abs/2604.24797', 'https://arxiv.org/abs/1910.09336v2', 'https://arxiv.org/abs/2508.21593v2',
    'https://arxiv.org/abs/1107.4721v2', 'https://arxiv.org/abs/1109.0633v1']) assert(refs.includes(`<a href="${url}" rel="noopener">`), url);
  assert(refs.includes('The mathlib Community (2019). The Lean mathematical library. arXiv:1910.09336v2</a>'));
  assert.strictEqual(count(refs, /<a /g), 5);                                           // exactly one link per reference line
  // 2. structure: paragraphs, a real bullet list, one reference per line, headings only where there is content
  assert(html.includes('<h2>References</h2>'));
  assert(/<ul>\s*<li>The divergence between human-designed taxonomies/.test(html) && count(html.split('Key concepts explored')[1].split('</ul>')[0], /<li>/g) === 4);
  assert(!/^\*\s/m.test(html) && !html.includes('## ') && !html.includes('\n- '));
  assert(count(html, /<p>/g) >= 6);
  // 3. the Further reading pointer
  assert(html.includes('<p class="pointer">Further reading: the other papers reviewed for this episode are listed below.</p>'));
  assert(!html.includes('www.copernicusai.fyi') && !html.includes('.*') && !html.includes('*Further'));
  assert(!renderDescriptionHtml(fx['ever-math-260010'].description_markdown, { hasFurtherReading: false }).includes('Further reading'));   // no list below: no pointer
  // 4. hashtags are not shown
  assert(!/hashtag/i.test(html) && !html.includes('#CopernicusAI') && !html.includes('#SciencePodcast'));
  assert(fx['ever-math-260010'].description_markdown.includes('Hashtags'));            // ... and the stored text still has them
}

// ---------------------------------------------------------------- older episodes
{
  const phys = renderDescriptionHtml(fx['ever-phys-250044'].description_markdown, { hasFurtherReading: false });
  assert.strictEqual(count(phys, /<ul class="references"><\/ul>/g), 0);
  const physRefs = phys.slice(phys.indexOf('<ul class="references">'));
  assert.strictEqual(count(physRefs, /<li>/g), 5);
  assert(physRefs.includes('<a href="http://arxiv.org/abs/2407.21701v2" rel="noopener">'), 'old "Available: [url](url)" lines link to their own URL');
  assert.strictEqual(count(physRefs, /<a /g), 5);
  assert(!/hashtag/i.test(phys) && !phys.includes('#CopernicusAI'));

  const bio = renderDescriptionHtml(fx['ever-bio-250014'].description_markdown, { hasFurtherReading: false });
  assert(!bio.includes('References') && !bio.includes('<ul') && !/hashtag/i.test(bio));                  // an empty References section shows no heading
  assert(count(bio, /<p>/g) >= 3);

  const med = renderDescriptionHtml(fx['ever-math-260002'].description_markdown, { hasFurtherReading: false });
  const medRefs = med.slice(med.indexOf('<ul class="references">'));
  assert(count(medRefs, /<li>/g) >= 10 && count(medRefs, /<li>/g) === count(medRefs, /<a href="https:\/\/doi\.org\/10\./g));   // every DOI reference is a link
  assert(!/hashtag/i.test(med));
}

// ---------------------------------------------------------------- the link rules
assert.strictEqual(referenceUrl('- Li (2026). T. arXiv:2604.24797'), 'https://arxiv.org/abs/2604.24797');
assert.strictEqual(referenceUrl('- X (2011). T. arXiv:1107.4721v2'), 'https://arxiv.org/abs/1107.4721v2');
assert.strictEqual(referenceUrl('- X (1999). T. arXiv:hep-th/9901001v1'), 'https://arxiv.org/abs/hep-th/9901001v1');
assert.strictEqual(referenceUrl('- X (2020). T. Nature. DOI: 10.1038/s41586-020-1234-5.'), 'https://doi.org/10.1038/s41586-020-1234-5');
assert.strictEqual(referenceUrl('- X (2020). T. J. PMID 12345678'), 'https://pubmed.ncbi.nlm.nih.gov/12345678/');
assert.strictEqual(referenceUrl('- X (2020). T. https://example.org/paper.pdf.'), 'https://example.org/paper.pdf');
assert.strictEqual(referenceUrl('- X (2020). T. DOI: [10.1/x](https://doi.org/10.1/x)'), 'https://doi.org/10.1/x');
assert.strictEqual(referenceUrl('- X (2020). A title with no identifier.'), '');
assert.strictEqual(referenceHtml('- X (2020). No id.'), 'X (2020). No id.');                       // no link when there is nothing to link to
assert.strictEqual(referenceUrl('- X. arXiv:2604.24797 and DOI: 10.1/y'), 'https://arxiv.org/abs/2604.24797');   // arXiv first, as in Further reading

// ---------------------------------------------------------------- safety
{
  const html = renderDescriptionHtml('Intro <script>alert(1)</script> [bad](javascript:alert(1)) **bold** & <b>x</b>\n\n## References\n\n- Evil <img src=x onerror=alert(1)> arXiv:2601.00001v1');
  assert(!html.includes('<script') && !/href="javascript/i.test(html) && !html.includes('<a href="javascript') && !html.includes('<img') && !html.includes('onerror='));
  assert(html.includes('<strong>bold</strong>') && html.includes('&amp;'));
}
console.log('render description: ok');
