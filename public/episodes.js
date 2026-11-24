/* The episode list, shared by the homepage and the archive.

   The homepage shows the most recent few and sends the reader to the archive for the rest; the archive shows them all with a search box
   and the field filter. Both read the same feed, sanitise the same notes and link the same sources, so the two pages can never drift
   apart. What differs is read from the grid element: data-limit="6" shows six, and the search and filter appear only where the page
   provides them. */
(function () {
  "use strict";
  var FEED = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml";
  var CATEGORIES = {bio:"Biology", chem:"Chemistry", phys:"Physics", math:"Mathematics", compsci:"Computer science", news:"News"};
  var grid = document.getElementById("grid"), statusEl = document.getElementById("status");
  if (!grid) return;                                   // a page without a grid has nothing for this script to do
  var q = document.getElementById("q"), chips = document.getElementById("chips"), count = document.getElementById("count");
  var LIMIT = parseInt(grid.getAttribute("data-limit") || "0", 10) || 0;
  var chosen = "";
  var episodes = [];

  // Only the tags the feed's notes actually use. Anything else is unwrapped, every attribute is dropped, and an href is kept only
  // when it is http(s) or mailto - so the notes cannot bring script, style, an iframe or a javascript: URL onto the page.
  var ALLOWED = {A:1, P:1, UL:1, LI:1, STRONG:1, EM:1, H1:1, H2:1, H3:1, BR:1};

  function sanitise(html) {
    var doc = new DOMParser().parseFromString("<div>" + html + "</div>", "text/html");
    var root = doc.body.firstChild;
    (function walk(node) {
      for (var i = node.childNodes.length - 1; i >= 0; i--) {
        var child = node.childNodes[i];
        if (child.nodeType === 1) {
          walk(child);
          if (!ALLOWED[child.tagName]) {                       // unwrap: the text survives, the element does not
            while (child.firstChild) node.insertBefore(child.firstChild, child);
            node.removeChild(child);
            continue;
          }
          var href = child.tagName === "A" ? child.getAttribute("href") : null;
          for (var a = child.attributes.length - 1; a >= 0; a--) child.removeAttribute(child.attributes[a].name);
          if (href && /^(https?:|mailto:)/i.test(href)) {
            child.setAttribute("href", href);
            child.setAttribute("rel", "noopener noreferrer");
          }
          if (child.tagName === "H1" || child.tagName === "H2") {   // a card sits under an h3; keep the outline sound
            var h = doc.createElement("h3");
            while (child.firstChild) h.appendChild(child.firstChild);
            node.replaceChild(h, child);
          }
        } else if (child.nodeType !== 3) {
          node.removeChild(child);                             // comments, CDATA and the rest
        }
      }
    })(root);
    linkify(root, doc);
    return root.innerHTML;
  }

  // A DOI becomes a link to doi.org. Where a reference gives no DOI but names the pinned commit it was read at, that commit becomes
  // the link instead, so every source on the page can be opened at the version the episode used.
  var DOI = /\b10\.\d{4,9}\/[^\s<>"')\]]+/g;
  var COMMIT = /\bcommit\s+([0-9a-f]{7,40})\b/gi;
  var URL = /\bhttps?:\/\/[^\s<>"')\]]+/g;
  function linkify(root, doc) {
    var walker = doc.createTreeWalker(root, NodeFilter.SHOW_TEXT, null), texts = [], n;
    while ((n = walker.nextNode())) if (!n.parentNode.closest("a")) texts.push(n);
    texts.forEach(function (node) {
      var text = node.nodeValue, out = null;
      var make = function (re, href) {
        var frag = doc.createDocumentFragment(), last = 0, m; re.lastIndex = 0;
        while ((m = re.exec(text))) {
          if (m.index > last) frag.appendChild(doc.createTextNode(text.slice(last, m.index)));
          var a = doc.createElement("a");
          a.setAttribute("href", href(m));
          a.setAttribute("rel", "noopener noreferrer");
          a.appendChild(doc.createTextNode(m[0]));
          frag.appendChild(a);
          last = m.index + m[0].length;
        }
        if (!frag.childNodes.length) return null;
        if (last < text.length) frag.appendChild(doc.createTextNode(text.slice(last)));
        return frag;
      };
      out = make(DOI, function (m) { return "https://doi.org/" + m[0].replace(/[.,;)]+$/, ""); });
      // A reference with no DOI gives the address it was read at instead - an arXiv abstract page, or the pinned commit of a company's
      // repository. Both are linked, so every source on the page can be opened at the version the episode used.
      if (!out) out = make(URL, function (m) { return m[0].replace(/[.,;)]+$/, ""); });
      if (!out) out = make(COMMIT, function (m) { return "https://github.com/openai/math/tree/" + m[1]; });
      if (out) node.parentNode.replaceChild(out, node);
    });
  }

  // One chip per field actually present, each in that field's colour, plus "All". Buttons rather than a menu, so the colour of a field
  // is visible before it is chosen and is the same colour the cards carry.
  function buildChips() {
    var present = Object.keys(CATEGORIES).map(function (k) { return CATEGORIES[k]; })
      .filter(function (label) { return episodes.some(function (ep) { return ep.category === label; }); });
    [""].concat(present).forEach(function (label) {
      var li = document.createElement("li");
      var b = document.createElement("button");
      b.type = "button";
      b.className = "chip";
      b.textContent = label || "All fields";
      b.setAttribute("aria-pressed", String(label === chosen));
      if (label) li.setAttribute("data-field", label);
      b.addEventListener("click", function () {
        chosen = label;
        Array.prototype.forEach.call(chips.querySelectorAll(".chip"), function (other) {
          other.setAttribute("aria-pressed", String(other === b));
        });
        render();
      });
      li.appendChild(b);
      chips.appendChild(li);
    });
  }

  function categoryOf(id) {
    var part = String(id || "").split("-")[1];
    return CATEGORIES[part] || "";
  }

  function text(item, tag, ns) {
    var el = ns ? item.getElementsByTagNameNS(ns, tag)[0] : item.getElementsByTagName(tag)[0];
    return el && el.textContent ? el.textContent.trim() : "";
  }

  function parse(xml) {
    var doc = new DOMParser().parseFromString(xml, "application/xml");
    if (doc.getElementsByTagName("parsererror").length) throw new Error("the feed could not be parsed");
    var CONTENT = "http://purl.org/rss/1.0/modules/content/", ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd";
    return Array.prototype.map.call(doc.getElementsByTagName("item"), function (item) {
      var enc = item.getElementsByTagName("enclosure")[0];
      var img = item.getElementsByTagNameNS(ITUNES, "image")[0];
      var id = text(item, "guid");
      return {
        id: id,
        title: text(item, "title"),
        summary: text(item, "description"),
        notes: text(item, "encoded", CONTENT),
        audio: enc ? enc.getAttribute("url") : "",
        duration: text(item, "duration", ITUNES),
        date: text(item, "pubDate"),
        image: img ? img.getAttribute("href") : "",
        category: categoryOf(id)
      };
    });
  }

  function card(ep) {
    var li = document.createElement("li");
    li.className = "card";
    if (ep.category) li.setAttribute("data-field", ep.category);   // the field's colour, for the stripe and the tag
    var when = ep.date ? new Date(ep.date) : null;
    var dateText = when && !isNaN(when) ? when.toLocaleDateString(undefined, {year:"numeric", month:"long", day:"numeric"}) : "";

    if (ep.image) {
      var img = document.createElement("img");
      img.src = ep.image;
      img.alt = "";                                    // decorative: the title beside it carries the meaning
      img.loading = "lazy";
      li.appendChild(img);
    }
    var body = document.createElement("div");
    body.className = "body";

    var h = document.createElement("h3");
    if (ep.audio) {
      var link = document.createElement("a");
      link.href = ep.audio;
      link.textContent = ep.title;
      h.appendChild(link);
    } else {
      h.textContent = ep.title;
    }
    body.appendChild(h);

    var meta = document.createElement("p");
    meta.className = "meta";
    if (ep.category) {
      var tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = ep.category;
      meta.appendChild(tag);
    }
    [dateText, ep.duration].forEach(function (bit) {
      if (!bit) return;
      var s = document.createElement("span");
      s.textContent = bit;
      meta.appendChild(s);
    });
    body.appendChild(meta);

    if (ep.summary) {
      var p = document.createElement("p");
      p.className = "summary";
      p.textContent = ep.summary.length > 260 ? ep.summary.slice(0, 260).replace(/\s+\S*$/, "") + "…" : ep.summary;
      body.appendChild(p);
    }
    if (ep.audio) {
      var audio = document.createElement("audio");
      audio.controls = true;
      audio.preload = "none";
      audio.src = ep.audio;
      body.appendChild(audio);
    }
    if (ep.notes) {
      var det = document.createElement("details");
      det.className = "notes";
      var sum = document.createElement("summary");
      sum.textContent = "Full notes and sources";
      det.appendChild(sum);
      var inner = document.createElement("div");
      inner.className = "inner";
      inner.innerHTML = sanitise(ep.notes);
      det.appendChild(inner);
      body.appendChild(det);
    }
    li.appendChild(body);
    return li;
  }

  function render() {
    var needle = q ? q.value.trim().toLowerCase() : "";
    var shown = episodes.filter(function (ep) {
      if (chosen && ep.category !== chosen) return false;
      if (!needle) return true;
      return (ep.title + " " + ep.summary + " " + ep.notes).toLowerCase().indexOf(needle) !== -1;
    });
    var visible = LIMIT ? shown.slice(0, LIMIT) : shown;
    grid.textContent = "";
    visible.forEach(function (ep) { grid.appendChild(card(ep)); });
    if (count) {
      count.textContent = LIMIT
        ? "Showing the " + visible.length + " most recent of " + episodes.length
        : (shown.length === episodes.length ? episodes.length + " episodes"
                                            : shown.length + " of " + episodes.length + " episodes");
    }
    if (statusEl) statusEl.textContent = visible.length ? "" : "No episode matches that search.";
  }

  fetch(FEED, {cache: "no-cache"})
    .then(function (r) { if (!r.ok) throw new Error("the feed returned " + r.status); return r.text(); })
    .then(function (xml) {
      episodes = parse(xml);
      if (chips) buildChips();
      statusEl.textContent = "";
      render();
    })
    .catch(function (err) {
      statusEl.textContent = "The episode list could not be loaded (" + err.message + "). The RSS feed link above still works.";
    });

  if (q) q.addEventListener("input", render);
})();
