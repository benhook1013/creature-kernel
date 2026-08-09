(function () {
  "use strict";

  var app = document.getElementById("app");

  function node(tag, text, className) {
    var element = document.createElement(tag);
    if (text !== undefined && text !== null) {
      element.textContent = String(text);
    }
    if (className) {
      element.className = className;
    }
    return element;
  }

  function api(path, options) {
    return fetch(path, options || {}).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (body) {
        if (!response.ok) {
          throw new Error(body.error || "Request failed");
        }
        return body;
      });
    });
  }

  function clear(element) {
    while (element.firstChild) {
      element.removeChild(element.firstChild);
    }
  }

  function addNotice(parent, message, kind) {
    parent.appendChild(node("p", message, kind || "notice"));
  }

  function renderIndex(data) {
    clear(app);
    var heading = node("h1", "Visual review gallery");
    app.appendChild(heading);
    addNotice(app, "Local image comparison sessions. Open a session to record choices and notes.", "lede");
    var sessions = data.sessions || [];
    if (!sessions.length) {
      addNotice(app, "No valid review sessions are available yet.", "empty");
    }
    var list = node("div", null, "session-list");
    sessions.forEach(function (session) {
      var card = node("article", null, "session-card");
      var title = node("h2");
      var link = node("a", session.title);
      link.href = "/review/" + encodeURIComponent(session.id);
      title.appendChild(link);
      card.appendChild(title);
      card.appendChild(node("code", session.id, "stable-id"));
      if (session.description) {
        card.appendChild(node("p", session.description));
      }
      list.appendChild(card);
    });
    app.appendChild(list);
    (data.errors || []).forEach(function (entry) {
      addNotice(app, "Unavailable session " + entry.id + ": " + entry.error, "error");
    });
  }

  function metadataBlock(item) {
    if (!item.metadata) {
      return null;
    }
    var pre = node("pre", JSON.stringify(item.metadata, null, 2), "metadata");
    pre.setAttribute("aria-label", "Metadata for " + item.id);
    return pre;
  }

  function subjectContextBlock(context) {
    if (!context) {
      return null;
    }
    var panel = node("section", null, "subject-context");
    panel.appendChild(node("h2", "What you're looking at"));
    if (context.authored_summary) {
      panel.appendChild(node("h3", "Authored summary"));
      panel.appendChild(node("p", context.authored_summary.text));
      if (context.authored_summary.unknowns && context.authored_summary.unknowns.length) {
        panel.appendChild(node("h4", "Unknowns"));
        var unknowns = node("ul");
        context.authored_summary.unknowns.forEach(function (unknown) {
          unknowns.appendChild(node("li", unknown));
        });
        panel.appendChild(unknowns);
      }
    }
    [
      ["descriptor_snapshot", "Generated descriptor snapshot"],
      ["provenance", "Build/render provenance"]
    ].forEach(function (entry) {
      if (!context[entry[0]]) {
        return;
      }
      var details = node("details");
      details.open = true;
      details.appendChild(node("summary", entry[1]));
      details.appendChild(node("pre", JSON.stringify(context[entry[0]], null, 2), "context-json"));
      panel.appendChild(details);
    });
    return panel;
  }

  function openImage(item, source) {
    var dialog = node("dialog", null, "image-dialog");
    var close = node("button", "Close", "close-dialog");
    close.type = "button";
    close.addEventListener("click", function () { dialog.close(); });
    dialog.appendChild(close);
    var image = node("img");
    image.src = source;
    image.alt = item.title;
    dialog.appendChild(image);
    dialog.addEventListener("close", function () { dialog.remove(); });
    document.body.appendChild(dialog);
    dialog.showModal();
  }

  function renderReview(data) {
    var review = data.review;
    var oldResponse = data.response || null;
    clear(app);
    var back = node("a", "← All reviews", "back-link");
    back.href = "/";
    app.appendChild(back);
    app.appendChild(node("h1", review.title));
    app.appendChild(node("code", review.id, "stable-id"));
    if (review.description) {
      app.appendChild(node("p", review.description, "lede"));
    }
    var contextPanel = subjectContextBlock(review.subject_context);
    if (contextPanel) {
      app.appendChild(contextPanel);
    }
    if (review.instructions) {
      var instructions = node("aside", null, "instructions");
      instructions.appendChild(node("h2", "Instructions"));
      instructions.appendChild(node("p", review.instructions));
      app.appendChild(instructions);
    }
    var form = node("form");
    form.addEventListener("submit", function (event) { event.preventDefault(); saveReview(review, form); });
    review.groups.forEach(function (group) {
      var section = node("section", null, "review-group");
      section.dataset.groupId = group.id;
      var heading = node("h2", group.title);
      heading.appendChild(node("code", group.id, "stable-id").cloneNode(true));
      section.appendChild(heading);
      if (group.description) {
        section.appendChild(node("p", group.description));
      }
      var cards = node("div", null, "option-grid");
      var selected = (oldResponse && oldResponse.selections[group.id]) || [];
      group.items.forEach(function (item) {
        var card = node("article", null, "option-card");
        var imageButton = node("button", null, "image-button");
        imageButton.type = "button";
        imageButton.setAttribute("aria-label", "Expand " + item.title);
        var image = node("img");
        image.src = "/api/reviews/" + encodeURIComponent(review.id) + "/assets/" + item.image.substring("assets/".length).split("/").map(encodeURIComponent).join("/");
        image.alt = item.title;
        image.loading = "lazy";
        imageButton.appendChild(image);
        imageButton.addEventListener("click", function () { openImage(item, image.src); });
        card.appendChild(imageButton);
        var body = node("div", null, "option-body");
        var itemTitle = node("h3", item.title);
        itemTitle.appendChild(node("code", item.id, "stable-id"));
        body.appendChild(itemTitle);
        if (item.description) {
          body.appendChild(node("p", item.description));
        }
        var metadata = metadataBlock(item);
        if (metadata) {
          body.appendChild(metadata);
        }
        if (group.selection_mode !== "none") {
          var label = node("label", null, "choice");
          var input = node("input");
          input.type = group.selection_mode === "single" ? "radio" : "checkbox";
          input.name = "selection-" + group.id;
          input.value = item.id;
          input.checked = selected.indexOf(item.id) !== -1;
          label.appendChild(input);
          label.appendChild(node("span", group.selection_mode === "single" ? "Choose this option" : "Include this option"));
          body.appendChild(label);
        }
        card.appendChild(body);
        cards.appendChild(card);
      });
      section.appendChild(cards);
      var noteLabel = node("label", "Notes for " + group.title, "note-label");
      var note = node("textarea");
      note.name = "note-" + group.id;
      note.rows = 3;
      note.placeholder = "Optional comparison notes";
      note.value = oldResponse && oldResponse.group_notes[group.id] ? oldResponse.group_notes[group.id] : "";
      noteLabel.appendChild(note);
      section.appendChild(noteLabel);
      form.appendChild(section);
    });
    var overallLabel = node("label", "Overall notes", "note-label overall-note");
    var overall = node("textarea");
    overall.name = "overall-note";
    overall.rows = 5;
    overall.placeholder = "What should the agent know about these choices?";
    overall.value = oldResponse ? oldResponse.overall_note : "";
    overallLabel.appendChild(overall);
    form.appendChild(overallLabel);
    var actions = node("div", null, "actions");
    var save = node("button", "Save response", "primary");
    save.type = "submit";
    actions.appendChild(save);
    var copy = node("button", "Copy summary", "secondary");
    copy.type = "button";
    copy.addEventListener("click", function () {
      var summary = collectResponse(review, form, true);
      copySummary(review, summary, copy);
    });
    actions.appendChild(copy);
    actions.appendChild(node("span", "", "save-status"));
    form.appendChild(actions);
    app.appendChild(form);
  }

  function collectResponse(review, form, includeTimestamp) {
    var selections = {};
    var groupNotes = {};
    review.groups.forEach(function (group) {
      selections[group.id] = [];
      if (group.selection_mode !== "none") {
        form.querySelectorAll("input[name='selection-" + group.id + "']").forEach(function (input) {
          if (input.checked) { selections[group.id].push(input.value); }
        });
      }
      var note = form.querySelector("textarea[name='note-" + group.id + "']");
      groupNotes[group.id] = note ? note.value : "";
    });
    var overall = form.querySelector("textarea[name='overall-note']");
    var response = {
      schema_version: 1,
      review_id: review.id,
      selections: selections,
      group_notes: groupNotes,
      overall_note: overall ? overall.value : ""
    };
    if (includeTimestamp) {
      response.saved_at = "";
    }
    return response;
  }

  function copySummary(review, response, button) {
    var lines = ["Visual review: " + review.title, "Review ID: " + review.id];
    review.groups.forEach(function (group) {
      lines.push(group.title + " (" + group.id + "): " + (response.selections[group.id].join(", ") || "no selection"));
      if (response.group_notes[group.id]) { lines.push("  Notes: " + response.group_notes[group.id]); }
    });
    if (response.overall_note) { lines.push("Overall notes: " + response.overall_note); }
    var text = lines.join("\n");
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { button.textContent = "Copied"; }).catch(function () { button.textContent = "Copy unavailable"; });
    } else {
      button.textContent = "Copy unavailable";
    }
  }

  function saveReview(review, form) {
    var status = form.querySelector(".save-status");
    var tokenElement = document.querySelector("meta[name='visual-review-write-token']");
    var token = tokenElement ? tokenElement.getAttribute("content") : "";
    var response = collectResponse(review, form, false);
    status.textContent = "Saving…";
    api("/api/reviews/" + encodeURIComponent(review.id) + "/response", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Visual-Review-Token": token },
      body: JSON.stringify(response)
    }).then(function (saved) {
      status.textContent = "Saved at " + saved.saved_at;
    }).catch(function (error) {
      status.textContent = "Save failed: " + error.message;
    });
  }

  function load() {
    if (window.location.pathname === "/" || window.location.pathname === "") {
      api("/api/sessions").then(renderIndex).catch(function (error) { clear(app); addNotice(app, error.message, "error"); });
      return;
    }
    var match = window.location.pathname.match(/^\/review\/([^/]+)\/?$/);
    if (!match) {
      clear(app);
      addNotice(app, "Not found", "error");
      return;
    }
    api("/api/reviews/" + encodeURIComponent(decodeURIComponent(match[1]))).then(renderReview).catch(function (error) { clear(app); addNotice(app, error.message, "error"); });
  }

  load();
}());
