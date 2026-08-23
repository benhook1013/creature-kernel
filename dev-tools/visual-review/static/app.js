(function () {
  "use strict";

  var app = document.getElementById("app");
  var imageDialogLockCount = 0;
  var imageDialogPreviousOverflow = null;

  function acquireImageDialogLock() {
    if (imageDialogLockCount === 0) {
      imageDialogPreviousOverflow = document.body.style.overflow;
    }
    imageDialogLockCount += 1;
    document.body.style.overflow = "hidden";
    var released = false;
    return function () {
      if (released) {
        return;
      }
      released = true;
      imageDialogLockCount -= 1;
      if (imageDialogLockCount === 0) {
        document.body.style.overflow = imageDialogPreviousOverflow;
        imageDialogPreviousOverflow = null;
      }
    };
  }

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
    document.title = "Creature Kernel visual reviews";
    clear(app);
    var heading = node("h1", "Visual review gallery");
    app.appendChild(heading);
    addNotice(app, "Local image comparison, structural inspection, and read-only filled-form sessions. Open a session to inspect or appraise its bounded content; image sessions can record choices and notes.", "lede");
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
      if (session.kind === "structure") {
        card.appendChild(node("span", "Structural inspection", "session-kind"));
      }
      if (session.kind === "provisional-form") {
        card.appendChild(node("span", "Filled primitive appraisal", "session-kind form-session-kind"));
      }
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

  function jsonText(value) {
    try {
      var text = JSON.stringify(value, null, 2);
      return text === undefined ? "Unavailable" : text;
    } catch (error) {
      return "Unavailable (could not serialize this value)";
    }
  }

  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function addressText(address) {
    if (!isObject(address)) {
      return "Unavailable address";
    }
    var namespace = address.namespace === undefined ? "?" : String(address.namespace);
    var kind = address.kind === undefined ? "?" : String(address.kind);
    var role = address.role === undefined ? "?" : String(address.role);
    var anchors = Array.isArray(address.anchors) ? address.anchors.map(String) : [];
    return namespace + " / " + kind + ":" + role + " [anchors: " + (anchors.length ? anchors.join(", ") : "none") + "]";
  }

  function declarationText(declaration) {
    if (!isObject(declaration)) {
      return "Unavailable module declaration";
    }
    var namespace = declaration.namespace === undefined ? "?" : String(declaration.namespace);
    var documentName = declaration.document === undefined ? "?" : String(declaration.document);
    var role = declaration.role === undefined ? "?" : String(declaration.role);
    var anchors = Array.isArray(declaration.anchors) ? declaration.anchors.map(String) : [];
    return namespace + " / module declaration:" + role + " [anchors: " + (anchors.length ? anchors.join(", ") : "none") + "] (document: " + documentName + ")";
  }

  function addressDetails(address, label) {
    var details = node("details", null, "structure-details");
    details.appendChild(node("summary", (label || "Address") + ": " + addressText(address)));
    details.appendChild(node("pre", jsonText(address), "context-json"));
    return details;
  }

  function valueDetails(label, value) {
    var details = node("details", null, "structure-details");
    details.appendChild(node("summary", label));
    details.appendChild(node("pre", jsonText(value), "context-json"));
    return details;
  }

  function collectionCount(value) {
    return Array.isArray(value) ? String(value.length) : "Unavailable";
  }

  function metadataGrid(entries) {
    var grid = node("dl", null, "structure-metadata");
    entries.forEach(function (entry) {
      grid.appendChild(node("dt", entry[0]));
      grid.appendChild(node("dd", entry[1]));
    });
    return grid;
  }

  function structureDiagnostics(structure, extra) {
    var diagnostics = Array.isArray(structure && structure.diagnostics) ? structure.diagnostics.slice() : [];
    (extra || []).forEach(function (message) {
      diagnostics.push({ code: "ck.visual-review.invalid-structure", message: message });
    });
    return diagnostics;
  }

  function diagnosticsBlock(structure, extra) {
    var diagnostics = structureDiagnostics(structure, extra);
    var section = node("section", null, "structure-diagnostics");
    section.appendChild(node("h2", "Status and diagnostics"));
    if (!diagnostics.length) {
      section.appendChild(node("p", "No diagnostics were supplied by the inspection result."));
      return section;
    }
    var list = node("ul");
    diagnostics.forEach(function (diagnostic) {
      var message;
      if (isObject(diagnostic)) {
        if (diagnostic.detail !== undefined && diagnostic.detail !== null && String(diagnostic.detail)) {
          message = String(diagnostic.detail);
        } else if (diagnostic.message !== undefined && diagnostic.message !== null && String(diagnostic.message)) {
          message = String(diagnostic.message);
        } else {
          message = jsonText(diagnostic);
        }
      } else {
        message = diagnostic === undefined || diagnostic === null ? jsonText(diagnostic) : String(diagnostic);
      }
      var code = isObject(diagnostic) && diagnostic.code ? String(diagnostic.code) + ": " : "";
      list.appendChild(node("li", code + message));
    });
    section.appendChild(list);
    return section;
  }

  function validateStructure(structure) {
    var errors = [];
    if (!isObject(structure)) {
      return ["The structure payload is not an object."];
    }
    if (structure.status !== "success") {
      return errors;
    }
    if (!isObject(structure.graph)) {
      errors.push("A successful structural result must contain a graph object.");
      return errors;
    }
    var graph = structure.graph;
    ["modules", "parts", "joints", "sockets", "attachments", "landmarks", "dimensions", "frames", "regions", "capabilities", "fields"].forEach(function (name) {
      if (!Array.isArray(graph[name])) {
        errors.push("graph." + name + " is missing or is not a collection.");
      }
    });
    if (errors.length || !Array.isArray(graph.parts)) {
      return errors;
    }
    var partKeys = Object.create(null);
    graph.parts.forEach(function (part, index) {
      if (!isObject(part) || !isObject(part.address) || part.address.kind !== "part") {
        errors.push("graph.parts[" + index + "] has no valid Part address.");
        return;
      }
      var key = addressKey(part.address);
      if (partKeys[key]) {
        errors.push("graph.parts contains a duplicate Part address: " + addressText(part.address));
      }
      partKeys[key] = true;
      if (!isObject(part.containment)) {
        errors.push("Part " + addressText(part.address) + " has no explicit containment record.");
      } else if (part.containment.root === true && part.containment.parent !== undefined) {
        errors.push("Part " + addressText(part.address) + " cannot be both an explicit root and an explicit child.");
      } else if (part.containment.root !== true && (!isObject(part.containment.parent) || part.containment.parent.kind !== "part")) {
        errors.push("Part " + addressText(part.address) + " is neither an explicit root nor an explicit Part child.");
      }
    });
    graph.parts.forEach(function (part) {
      if (!isObject(part) || !isObject(part.containment) || !part.containment.parent) {
        return;
      }
      if (!partKeys[addressKey(part.containment.parent)]) {
        errors.push("Part " + addressText(part.address) + " names a missing containment parent.");
      }
    });
    if (!errors.length) {
      var visiting = Object.create(null);
      var visited = Object.create(null);
      function visit(key) {
        if (visiting[key]) {
          errors.push("Part containment contains a cycle.");
          return;
        }
        if (visited[key]) {
          return;
        }
        visiting[key] = true;
        var part = graph.parts.filter(function (candidate) { return addressKey(candidate.address) === key; })[0];
        if (part && part.containment.parent) {
          visit(addressKey(part.containment.parent));
        }
        delete visiting[key];
        visited[key] = true;
      }
      graph.parts.forEach(function (part) { visit(addressKey(part.address)); });
    }
    return errors;
  }

  function addressKey(address) {
    if (!isObject(address)) {
      return "<invalid>";
    }
    return [address.namespace, address.kind, address.role, Array.isArray(address.anchors) ? address.anchors.join("\u0001") : ""].map(function (value) {
      return String(value);
    }).join("\u0002");
  }

  function renderPart(part, childrenByParent) {
    var details = node("details", null, "containment-node");
    details.open = true;
    var summary = node("summary", String(part.address.role || "Part") + " — " + addressText(part.address));
    details.appendChild(summary);
    details.appendChild(addressDetails(part.address));
    if (part.placement !== undefined) {
      details.appendChild(valueDetails("Placement", part.placement));
    } else {
      details.appendChild(node("p", "Placement not supplied by this projection.", "muted"));
    }
    var children = childrenByParent[addressKey(part.address)] || [];
    if (children.length) {
      var childList = node("div", null, "containment-children");
      children.forEach(function (child) { childList.appendChild(renderPart(child, childrenByParent)); });
      details.appendChild(childList);
    }
    return details;
  }

  function containmentSection(graph) {
    var section = node("section", null, "structure-section");
    section.appendChild(node("h2", "Part containment"));
    section.appendChild(node("p", "Tree edges are drawn only from explicit Part containment records; joints and attachments are shown separately."));
    if (!graph.parts.length) {
      section.appendChild(node("p", "No Parts are present (0).", "empty"));
      return section;
    }
    var childrenByParent = Object.create(null);
    var roots = [];
    graph.parts.forEach(function (part) {
      if (part.containment.root === true) {
        roots.push(part);
      } else {
        var key = addressKey(part.containment.parent);
        if (!childrenByParent[key]) { childrenByParent[key] = []; }
        childrenByParent[key].push(part);
      }
    });
    var tree = node("div", null, "containment-tree");
    roots.forEach(function (root) { tree.appendChild(renderPart(root, childrenByParent)); });
    section.appendChild(tree);
    return section;
  }

  function addressList(parent, values, label) {
    if (!Array.isArray(values) || !values.length) {
      parent.appendChild(node("p", "No " + label + " (0).", "muted"));
      return;
    }
    var list = node("ul", null, "address-list");
    values.forEach(function (value) {
      var item = node("li");
      item.appendChild(node("span", addressText(value)));
      item.appendChild(addressDetails(value, "Details"));
      list.appendChild(item);
    });
    parent.appendChild(list);
  }

  function simpleCollectionSection(title, collections, description) {
    var section = node("section", null, "structure-section");
    section.appendChild(node("h2", title));
    if (description) {
      section.appendChild(node("p", description));
    }
    var grid = node("div", null, "structure-card-grid");
    collections.forEach(function (collection) {
      var card = node("article", null, "structure-card");
      card.appendChild(node("h3", collection.label + " (" + collection.items.length + ")"));
      if (!collection.items.length) {
        card.appendChild(node("p", "None present (0).", "muted"));
      } else {
        var list = node("ul", null, "address-list");
        collection.items.forEach(function (item) {
          var address = item && item.address;
          var row = node("li");
          var label = address ? addressText(address) : (item && item.declaration ? declarationText(item.declaration) : "Entry without an address");
          row.appendChild(node("span", label));
          row.appendChild(valueDetails("Record", item));
          list.appendChild(row);
        });
        card.appendChild(list);
      }
      grid.appendChild(card);
    });
    section.appendChild(grid);
    return section;
  }

  function jointSection(graph) {
    var section = node("section", null, "structure-section");
    section.appendChild(node("h2", "Articulation — joints (" + graph.joints.length + ")"));
    section.appendChild(node("p", "Each row preserves the directed proximal → distal endpoints from the source projection."));
    if (!graph.joints.length) {
      section.appendChild(node("p", "No joints are present (0).", "empty"));
      return section;
    }
    var table = node("table", null, "joint-table");
    var head = node("thead");
    var headingRow = node("tr");
    ["Joint", "Proximal → distal", "Frame details"].forEach(function (label) { headingRow.appendChild(node("th", label)); });
    head.appendChild(headingRow);
    table.appendChild(head);
    var body = node("tbody");
    graph.joints.forEach(function (joint) {
      var row = node("tr");
      row.appendChild(node("th", addressText(joint.address)));
      row.appendChild(node("td", addressText(joint.proximal) + " → " + addressText(joint.distal)));
      var frameCell = node("td");
      frameCell.appendChild(valueDetails("Proximal frame", joint.proximal_frame));
      frameCell.appendChild(valueDetails("Distal frame", joint.distal_frame));
      row.appendChild(frameCell);
      body.appendChild(row);
    });
    table.appendChild(body);
    section.appendChild(table);
    return section;
  }

  function regionsCapabilitiesSection(graph) {
    var section = node("section", null, "structure-section");
    section.appendChild(node("h2", "Regions and capabilities"));
    var grid = node("div", null, "structure-card-grid");
    [["Regions", graph.regions, "parts", "member Parts"], ["Capabilities", graph.capabilities, "subjects", "member subjects"]].forEach(function (entry) {
      var card = node("article", null, "structure-card");
      card.appendChild(node("h3", entry[0] + " (" + entry[1].length + ")"));
      if (!entry[1].length) {
        card.appendChild(node("p", "None present (0).", "muted"));
      }
      entry[1].forEach(function (item) {
        var block = node("div", null, "member-block");
        block.appendChild(node("h4", addressText(item.address) + " — " + (Array.isArray(item[entry[2]]) ? item[entry[2]].length : 0) + " " + entry[3]));
        addressList(block, item[entry[2]], entry[3]);
        card.appendChild(block);
      });
      grid.appendChild(card);
    });
    section.appendChild(grid);
    return section;
  }

  function preparedText(value, fallback) {
    if (value === undefined || value === null || value === "") {
      return fallback || "Unavailable";
    }
    if (typeof value === "object") {
      return jsonText(value);
    }
    return String(value);
  }

  function preparedField(row, names) {
    for (var index = 0; index < names.length; index += 1) {
      if (row[names[index]] !== undefined && row[names[index]] !== null) {
        return row[names[index]];
      }
    }
    return undefined;
  }

  function preparedNumericRows(value) {
    if (Array.isArray(value)) {
      return value;
    }
    if (!isObject(value)) {
      return null;
    }
    var rows = [];
    Object.keys(value).forEach(function (key) {
      var collection = value[key];
      if (Array.isArray(collection)) {
        collection.forEach(function (row) {
          if (isObject(row) && preparedField(row, ["group"]) === undefined) {
            var grouped = {};
            Object.keys(row).forEach(function (field) { grouped[field] = row[field]; });
            grouped.group = key;
            rows.push(grouped);
          } else {
            rows.push(row);
          }
        });
      } else if (isObject(collection)) {
        var groupedRow = {};
        Object.keys(collection).forEach(function (field) { groupedRow[field] = collection[field]; });
        if (preparedField(groupedRow, ["group"]) === undefined) {
          groupedRow.group = key;
        }
        rows.push(groupedRow);
      } else {
        rows.push(collection);
      }
    });
    return rows;
  }

  function preparedLocation(row) {
    var ownerRole = preparedField(row, ["owner_role", "ownerRole", "owner-role"]);
    var rowAddress = preparedField(row, ["semantic_key", "semanticKey", "address"]);
    if (ownerRole !== undefined) {
      if (isObject(ownerRole)) {
        var owner = preparedField(ownerRole, ["owner", "address", "semantic_key", "semanticKey"]);
        var role = preparedField(ownerRole, ["role", "owner_role", "ownerRole"]);
        if (role === undefined) {
          role = preparedField(row, ["role"]);
        }
        if (owner === undefined && role !== undefined && rowAddress !== undefined) {
          owner = rowAddress;
        }
        if (owner !== undefined && role !== undefined) {
          var ownerText = isObject(owner) && (owner.namespace !== undefined || owner.kind !== undefined || owner.role !== undefined) ? addressText(owner) : preparedText(owner);
          return "Owner " + ownerText + " · role " + preparedText(role);
        }
      } else if (rowAddress !== undefined) {
        var addressTextValue = isObject(rowAddress) && (rowAddress.namespace !== undefined || rowAddress.kind !== undefined || rowAddress.role !== undefined) ? addressText(rowAddress) : preparedText(rowAddress);
        return "Owner " + addressTextValue + " · role " + preparedText(ownerRole);
      }
      return preparedText(ownerRole, "Owner-role unavailable");
    }
    var rowOwner = preparedField(row, ["owner"]);
    var rowRole = preparedField(row, ["role"]);
    if (rowOwner !== undefined && rowRole !== undefined) {
      var rowOwnerText = isObject(rowOwner) && (rowOwner.namespace !== undefined || rowOwner.kind !== undefined || rowOwner.role !== undefined) ? addressText(rowOwner) : preparedText(rowOwner);
      return "Owner " + rowOwnerText + " · role " + preparedText(rowRole);
    }
    var location = preparedField(row, ["semantic_key", "semanticKey", "address", "location", "key"]);
    if (isObject(location)) {
      if (location.namespace !== undefined || location.kind !== undefined || location.role !== undefined) {
        return addressText(location);
      }
      return jsonText(location);
    }
    return preparedText(location, "Location unavailable");
  }

  function validatePrepared(prepared) {
    var errors = [];
    if (!isObject(prepared)) {
      return ["The prepared source payload is not an object."];
    }
    if (!isObject(prepared.basis)) {
      errors.push("prepared.basis is missing or is not an object.");
    } else {
      ["length_unit", "handedness", "up", "forward", "source_for_canonical"].forEach(function (name) {
        if (prepared.basis[name] === undefined || prepared.basis[name] === null) {
          errors.push("prepared.basis." + name + " is missing.");
        }
      });
    }
    if (!isObject(prepared.counts)) {
      errors.push("prepared.counts is missing or is not an object.");
    }
    var numericRows = preparedNumericRows(prepared.numeric_values);
    if (!numericRows) {
      errors.push("prepared.numeric_values is missing or is not a collection.");
    } else {
      numericRows.forEach(function (row, index) {
        if (!isObject(row)) {
          errors.push("prepared.numeric_values[" + index + "] is not an object.");
          return;
        }
        if (preparedField(row, ["group"]) === undefined) {
          errors.push("prepared.numeric_values[" + index + "] has no collection group.");
        }
        if (preparedField(row, ["semantic_key", "semanticKey", "address", "owner_role", "ownerRole", "owner-role", "owner", "location", "key"]) === undefined) {
          errors.push("prepared.numeric_values[" + index + "] has no semantic location.");
        }
        if (preparedField(row, ["field"]) === undefined) {
          errors.push("prepared.numeric_values[" + index + "] has no field.");
        }
        if (preparedField(row, ["component"]) === undefined) {
          errors.push("prepared.numeric_values[" + index + "] has no component.");
        }
        if (preparedField(row, ["display_value", "displayValue", "value"]) === undefined) {
          errors.push("prepared.numeric_values[" + index + "] has no display value.");
        }
        if (preparedField(row, ["binary64_bits", "binary64Bits", "bits"]) === undefined) {
          errors.push("prepared.numeric_values[" + index + "] has no binary64 bits.");
        }
      });
    }
    return errors;
  }

  function preparedBasisSection(basis) {
    var section = node("section", null, "prepared-card prepared-basis");
    section.appendChild(node("h3", "Declared source basis — inspected, not applied"));
    section.appendChild(node("p", "These declarations are shown exactly as prepared metadata. This checkpoint inspects them but applies no unit or coordinate-basis conversion.", "prepared-explanation"));
    var table = node("table", null, "prepared-table prepared-basis-table");
    var head = node("thead");
    var heading = node("tr");
    ["Declaration", "Inspected value"].forEach(function (label) { heading.appendChild(node("th", label)); });
    head.appendChild(heading);
    table.appendChild(head);
    var body = node("tbody");
    [["Length unit", basis.length_unit], ["Handedness", basis.handedness], ["Up", basis.up], ["Forward", basis.forward], ["Source for canonical", basis.source_for_canonical]].forEach(function (entry) {
      var row = node("tr");
      row.appendChild(node("th", entry[0]));
      row.appendChild(node("td", preparedText(entry[1])));
      body.appendChild(row);
    });
    table.appendChild(body);
    section.appendChild(table);
    return section;
  }

  function preparedCountsSection(counts) {
    var section = node("section", null, "prepared-card prepared-counts");
    section.appendChild(node("h3", "Prepared counts"));
    section.appendChild(node("p", "Prepared collection cardinalities; zero is a valid result.", "prepared-explanation"));
    var entries = Object.keys(counts);
    if (!entries.length) {
      section.appendChild(node("p", "No prepared counts were supplied.", "empty"));
      return section;
    }
    var grid = node("dl", null, "prepared-count-grid");
    entries.forEach(function (name) {
      grid.appendChild(node("dt", name.replace(/_/g, " ")));
      grid.appendChild(node("dd", preparedText(counts[name])));
    });
    section.appendChild(grid);
    return section;
  }

  function preparedNumericSection(rows) {
    var section = node("section", null, "prepared-card prepared-numeric");
    section.appendChild(node("h3", "Prepared numeric values"));
    section.appendChild(node("p", "Values are grouped by collection. Display values and binary64 bit patterns are reported from preparation; they are not transformed or resolved here.", "prepared-explanation"));
    if (!rows.length) {
      section.appendChild(node("p", "No prepared numeric values were supplied.", "empty"));
      return section;
    }
    var groups = Object.create(null);
    var order = [];
    rows.forEach(function (row) {
      var group = preparedText(preparedField(row, ["group"]), "Unspecified collection");
      if (!groups[group]) {
        groups[group] = [];
        order.push(group);
      }
      groups[group].push(row);
    });
    var container = node("div", null, "prepared-groups");
    order.forEach(function (group) {
      var details = node("details", null, "prepared-group");
      var values = groups[group];
      details.appendChild(node("summary", group + " (" + values.length + ")"));
      var table = node("table", null, "prepared-table prepared-values-table");
      var head = node("thead");
      var heading = node("tr");
      ["Location", "Field", "Component", "Display value", "binary64 bits"].forEach(function (label) { heading.appendChild(node("th", label)); });
      head.appendChild(heading);
      table.appendChild(head);
      var body = node("tbody");
      values.forEach(function (row) {
        var tableRow = node("tr");
        tableRow.appendChild(node("th", preparedLocation(row)));
        tableRow.appendChild(node("td", preparedText(preparedField(row, ["field"]), "Unavailable")));
        tableRow.appendChild(node("td", preparedText(preparedField(row, ["component"]), "Unavailable")));
        tableRow.appendChild(node("td", preparedText(preparedField(row, ["display_value", "displayValue", "value"]), "Unavailable")));
        tableRow.appendChild(node("td", preparedText(preparedField(row, ["binary64_bits", "binary64Bits", "bits"]), "Unavailable")));
        body.appendChild(tableRow);
      });
      table.appendChild(body);
      details.appendChild(table);
      container.appendChild(details);
    });
    section.appendChild(container);
    return section;
  }

  function preparedSourceSection(structure) {
    if (!isObject(structure) || !Object.prototype.hasOwnProperty.call(structure, "prepared")) {
      return null;
    }
    var prepared = structure.prepared;
    var section = node("section", null, "prepared-source");
    var heading = node("div", null, "prepared-heading");
    var title = node("h2", "Prepared source");
    title.appendChild(node("span", "Inspected · not applied", "prepared-status-pill"));
    heading.appendChild(title);
    heading.appendChild(node("p", "This checkpoint shows source values admitted and prepared into deterministic numeric carriers. It is an inspection of declared source data, not a resolved creature or runtime preview.", "prepared-explanation"));
    section.appendChild(heading);
    section.appendChild(metadataGrid([
      ["Status", preparedText(structure.status, "Unavailable")],
      ["Stage", preparedText(structure.stage, "Unavailable")],
      ["Format", preparedText(structure.format, "Unavailable")]
    ]));
    var errors = validatePrepared(prepared);
    if (errors.length) {
      var invalid = node("div", null, "prepared-invalid");
      invalid.appendChild(node("h3", "Prepared source unavailable"));
      invalid.appendChild(node("p", "The prepared-source data is incomplete or malformed. Existing structural and image review content remains available.", "prepared-explanation"));
      var list = node("ul");
      errors.slice(0, 8).forEach(function (error) { list.appendChild(node("li", error)); });
      if (errors.length > 8) { list.appendChild(node("li", (errors.length - 8) + " additional prepared-data issue(s) omitted.")); }
      invalid.appendChild(list);
      section.appendChild(invalid);
    } else {
      section.appendChild(preparedBasisSection(prepared.basis));
      section.appendChild(preparedCountsSection(prepared.counts));
      section.appendChild(preparedNumericSection(preparedNumericRows(prepared.numeric_values) || []));
    }
    var limitations = node("aside", null, "prepared-limitations");
    limitations.appendChild(node("h3", "Current limitation"));
    limitations.appendChild(node("p", "No resolver or snapshot, geometry, rig, animation, physics, unit/basis conversion, or runtime behavior is present in this checkpoint."));
    section.appendChild(limitations);
    return section;
  }

  var SVG_NAMESPACE = "http://www.w3.org/2000/svg";
  var SPATIAL_PREVIEW_FORMAT = "creature-kernel.provisional-exact-placement-preview.v1";

  function svgNode(tag, attributes) {
    var element = document.createElementNS(SVG_NAMESPACE, tag);
    Object.keys(attributes || {}).forEach(function (name) {
      element.setAttribute(name, String(attributes[name]));
    });
    return element;
  }

  var SPATIAL_IDENTIFIER_MAX_LENGTH = 16384;
  var SPATIAL_MAX_ANCHORS = 4096;
  var SPATIAL_ADDRESS_FIELDS = ["namespace", "anchors", "kind", "role"];
  var SPATIAL_ADDRESS_KINDS = ["part", "joint", "socket", "attachment", "region", "capability", "field"];

  function spatialExactFields(value, fields) {
    if (!isObject(value)) {
      return false;
    }
    var keys = Object.keys(value);
    return keys.length === fields.length && fields.every(function (field) {
      return Object.prototype.hasOwnProperty.call(value, field);
    });
  }

  function spatialIdentifier(value) {
    return typeof value === "string" && value.length > 0 && value.length <= SPATIAL_IDENTIFIER_MAX_LENGTH && /^[a-z][a-z0-9_]*$/.test(value);
  }

  function spatialAddressShape(value, expectedKind) {
    if (!spatialExactFields(value, SPATIAL_ADDRESS_FIELDS) || !spatialIdentifier(value.namespace) || !Array.isArray(value.anchors) || value.anchors.length > SPATIAL_MAX_ANCHORS || !value.anchors.every(spatialIdentifier) || SPATIAL_ADDRESS_KINDS.indexOf(value.kind) === -1 || !spatialIdentifier(value.role)) {
      return false;
    }
    return expectedKind === undefined || value.kind === expectedKind;
  }

  function spatialAddress(value) {
    return spatialAddressShape(value, "part");
  }

  function spatialSemanticAddress(value, expectedKind) {
    return spatialAddressShape(value, expectedKind);
  }

  function spatialAddressKey(address) {
    // JSON framing is unambiguous for the validated exact address tuple;
    // unlike delimiter joining, it cannot collide across anchor boundaries.
    return JSON.stringify([address.namespace, address.anchors, address.kind, address.role]);
  }

  function spatialInteger(value) {
    return typeof value === "number" && isFinite(value) && Math.floor(value) === value;
  }

  function spatialVector(value) {
    return Array.isArray(value) && value.length === 3 && value.every(spatialInteger);
  }

  function spatialAddressLabel(address) {
    if (!spatialAddress(address)) {
      return "Part";
    }
    var role = String(address.role);
    var anchors = Array.isArray(address.anchors) ? address.anchors.map(String) : [];
    return role + (anchors.length ? " · " + anchors.join(", ") : "");
  }

  function spatialAddressMap(parts) {
    var result = Object.create(null);
    parts.forEach(function (part) {
      result[spatialAddressKey(part.address)] = part;
    });
    return result;
  }

  function spatialCompare(left, right) {
    return left < right ? -1 : (left > right ? 1 : 0);
  }

  function spatialPreviewValidation(preview) {
    var errors = [];
    if (!isObject(preview)) {
      return { valid: false, unavailable: false, errors: ["The spatial preview payload is missing or is not an object."] };
    }
    if (preview.format !== SPATIAL_PREVIEW_FORMAT) {
      errors.push("preview.format is not the expected exact-placement preview format.");
    }
    if (preview.status === "unavailable") {
      if (!isObject(preview.diagnostic) || preview.diagnostic.code === undefined || preview.diagnostic.message === undefined) {
        errors.push("An unavailable preview must contain diagnostic.code and diagnostic.message.");
      }
      return { valid: false, unavailable: errors.length === 0, errors: errors };
    }
    if (preview.status !== "available") {
      errors.push("preview.status must be available or unavailable.");
    }
    if (!isObject(preview.basis)) {
      errors.push("preview.basis is missing or is not an object.");
    }
    if (!Array.isArray(preview.parts)) {
      errors.push("preview.parts is missing or is not a collection.");
    }
    if (!Array.isArray(preview.containment_edges)) {
      errors.push("preview.containment_edges is missing or is not a collection.");
    }
    if (!Array.isArray(preview.joint_edges)) {
      errors.push("preview.joint_edges is missing or is not a collection.");
    }
    if (!Array.isArray(preview.attachments)) {
      errors.push("preview.attachments is missing or is not a collection.");
    }
    if (errors.length) {
      return { valid: false, unavailable: false, errors: errors };
    }

    var parts = preview.parts;
    var partKeys = Object.create(null);
    parts.forEach(function (part, index) {
      if (!isObject(part) || !spatialAddress(part.address)) {
        errors.push("preview.parts[" + index + "] has no valid Part address.");
        return;
      }
      var key = spatialAddressKey(part.address);
      if (partKeys[key]) {
        errors.push("preview.parts contains a duplicate Part address.");
      }
      partKeys[key] = true;
      if (!spatialVector(part.position)) {
        errors.push("preview.parts[" + index + "].position must be three finite integer components.");
      }
      if (part.parent !== null && part.parent !== undefined && !spatialAddress(part.parent)) {
        errors.push("preview.parts[" + index + "].parent must be null or a Part address.");
      }
      if (["authored-root", "authored-containment", "authored-attachment"].indexOf(part.placement_source) === -1) {
        errors.push("preview.parts[" + index + "].placement_source is not recognized.");
      }
    });
    parts.forEach(function (part, index) {
      if (isObject(part) && spatialAddress(part.parent) && !partKeys[spatialAddressKey(part.parent)]) {
        errors.push("preview.parts[" + index + "] names a parent that is not in preview.parts.");
      }
    });

    function edgeAddress(edge, field, index) {
      if (!spatialAddress(edge[field])) {
        errors.push("preview edge " + index + " has no valid " + field + " Part address.");
        return;
      }
      if (!partKeys[spatialAddressKey(edge[field])]) {
        errors.push("preview edge " + index + " names a Part that is not in preview.parts.");
      }
    }
    preview.containment_edges.forEach(function (edge, index) {
      if (!isObject(edge)) {
        errors.push("preview.containment_edges[" + index + "] is not an object.");
        return;
      }
      edgeAddress(edge, "parent", index);
      edgeAddress(edge, "child", index);
    });
    preview.joint_edges.forEach(function (edge, index) {
      if (!isObject(edge)) {
        errors.push("preview.joint_edges[" + index + "] is not an object.");
        return;
      }
      if (!spatialSemanticAddress(edge.joint, "joint")) {
        errors.push("preview.joint_edges[" + index + "].joint is missing.");
      }
      edgeAddress(edge, "proximal", index);
      edgeAddress(edge, "distal", index);
    });
    preview.attachments.forEach(function (attachment, index) {
      if (!isObject(attachment)) {
        errors.push("preview.attachments[" + index + "] is not an object.");
        return;
      }
      var attachmentAddress = attachment.attachment;
      var root = attachment.root;
      var hostSocket = attachment.host_socket;
      var matingSocket = attachment.mating_socket;
      if (!spatialSemanticAddress(attachmentAddress, "attachment") || !spatialAddress(root) || !spatialSemanticAddress(hostSocket, "socket") || !spatialSemanticAddress(matingSocket, "socket")) {
        errors.push("preview.attachments[" + index + "] must identify an attachment and attached-root address.");
      } else if (!partKeys[spatialAddressKey(root)]) {
        errors.push("preview.attachments[" + index + "] names a root that is not in preview.parts.");
      }
      var translation = attachment.offset || attachment.translation || attachment.derived_root_local || attachment.derivedRootLocal;
      var authoredRootLocal = attachment.authored_root_local || attachment.authoredRootLocal;
      var derivedRootLocal = attachment.derived_root_local || attachment.derivedRootLocal;
      if (!spatialVector(translation) || !spatialVector(authoredRootLocal) || !spatialVector(derivedRootLocal)) {
        errors.push("preview.attachments[" + index + "] must include offset, authored-root, and derived-root integer translations.");
      }
    });
    return { valid: errors.length === 0, unavailable: false, errors: errors, parts: parts, partKeys: partKeys };
  }

  function spatialGroup(address) {
    var text = [address.role].concat(Array.isArray(address.anchors) ? address.anchors : []).join(" ").toLowerCase();
    if (/(^|[^a-z])tail([^a-z]|$)/.test(text)) {
      return "tail";
    }
    if (/(^|[^a-z])(left|l)([^a-z]|$)/.test(text) || /(^|[_-])l($|[_-])/.test(text)) {
      return "left";
    }
    if (/(^|[^a-z])(right|r)([^a-z]|$)/.test(text) || /(^|[_-])r($|[_-])/.test(text)) {
      return "right";
    }
    if (/(^|[^a-z])(core|root|pelvis|torso|body|spine|chest|neck|head)([^a-z]|$)/.test(text)) {
      return "core";
    }
    return "tail";
  }

  function spatialGroupColor(group) {
    return {
      core: "#69b8ff",
      left: "#b18cff",
      right: "#ffae72",
      tail: "#f17ba9"
    }[group] || "#b8c9d9";
  }

  function spatialNormalizedParts(parts) {
    var largest = 0;
    var ordered = parts.slice().sort(function (left, right) { return spatialCompare(spatialAddressKey(left.address), spatialAddressKey(right.address)); });
    ordered.forEach(function (part) {
      part.position.forEach(function (value) {
        largest = Math.max(largest, Math.abs(value));
      });
    });
    var divisor = largest > 0 && isFinite(largest) ? largest : 1;
    return ordered.map(function (part, index) {
      return {
        marker_id: "P" + (index + 1),
        address: part.address,
        parent: part.parent,
        placement_source: part.placement_source,
        exact_position: part.position.slice(),
        position: part.position.map(function (value) { return value / divisor; })
      };
    });
  }

  function spatialBounds(parts, horizontal, vertical) {
    var values = { horizontal: [], vertical: [] };
    parts.forEach(function (part) {
      values.horizontal.push(part.position[horizontal]);
      values.vertical.push(part.position[vertical]);
    });
    function extent(coordinates) {
      if (!coordinates.length) {
        return { min: -1, max: 1 };
      }
      var min = Math.min.apply(Math, coordinates);
      var max = Math.max.apply(Math, coordinates);
      if (!isFinite(min) || !isFinite(max)) {
        return { min: -1, max: 1 };
      }
      if (min === max) {
        var radius = Math.max(Math.abs(min) * 0.2, 1);
        return { min: min - radius, max: max + radius };
      }
      var padding = Math.max((max - min) * 0.12, 0.15);
      return { min: min - padding, max: max + padding };
    }
    return { horizontal: extent(values.horizontal), vertical: extent(values.vertical) };
  }

  function spatialViewTransform(parts, horizontal, vertical) {
    var bounds = spatialBounds(parts, horizontal, vertical);
    var plot = { left: 42, top: 24, width: 338, height: 218 };
    var horizontalRange = Math.max(bounds.horizontal.max - bounds.horizontal.min, 1e-12);
    var verticalRange = Math.max(bounds.vertical.max - bounds.vertical.min, 1e-12);
    var pixelsPerUnit = Math.min(plot.width / horizontalRange, plot.height / verticalRange);
    if (!isFinite(pixelsPerUnit) || pixelsPerUnit <= 0) {
      pixelsPerUnit = 1;
    }
    var usedWidth = horizontalRange * pixelsPerUnit;
    var usedHeight = verticalRange * pixelsPerUnit;
    var left = plot.left + (plot.width - usedWidth) / 2;
    var top = plot.top + (plot.height - usedHeight) / 2;
    function coordinate(value, axis) {
      if (!isFinite(value)) {
        return axis === "horizontal" ? left + usedWidth / 2 : top + usedHeight / 2;
      }
      if (axis === "horizontal") {
        return left + (value - bounds.horizontal.min) * pixelsPerUnit;
      }
      return top + usedHeight - (value - bounds.vertical.min) * pixelsPerUnit;
    }
    function axisZero(axis) {
      var extent = bounds[axis];
      return Math.max(extent.min, Math.min(extent.max, 0));
    }
    return {
      bounds: bounds,
      plot: plot,
      x: function (value) { return coordinate(value, "horizontal"); },
      y: function (value) { return coordinate(value, "vertical"); },
      zeroX: function () { return coordinate(axisZero("horizontal"), "horizontal"); },
      zeroY: function () { return coordinate(axisZero("vertical"), "vertical"); }
    };
  }

  function spatialDrawAxes(svg, transform, horizontalLabel, verticalLabel) {
    var plot = transform.plot;
    svg.appendChild(svgNode("rect", {
      x: plot.left, y: plot.top, width: plot.width, height: plot.height, class: "preview-plot"
    }));
    svg.appendChild(svgNode("line", {
      x1: plot.left, y1: transform.zeroY(), x2: plot.left + plot.width, y2: transform.zeroY(), class: "preview-axis"
    }));
    svg.appendChild(svgNode("line", {
      x1: transform.zeroX(), y1: plot.top, x2: transform.zeroX(), y2: plot.top + plot.height, class: "preview-axis"
    }));
    var horizontal = svgNode("text", { x: plot.left + plot.width - 4, y: plot.top + plot.height + 18, class: "preview-axis-label", "text-anchor": "end" });
    horizontal.textContent = horizontalLabel;
    svg.appendChild(horizontal);
    var vertical = svgNode("text", { x: plot.left - 8, y: plot.top + 10, class: "preview-axis-label", "text-anchor": "end" });
    vertical.textContent = verticalLabel;
    svg.appendChild(vertical);
  }

  function spatialEdgePosition(partMap, address) {
    var part = partMap[spatialAddressKey(address)];
    return part && part.position;
  }

  function spatialDrawEdges(svg, transform, preview, partMap, horizontal, vertical) {
    preview.containment_edges.slice().sort(function (left, right) {
      return spatialCompare(spatialAddressKey(left.parent) + spatialAddressKey(left.child), spatialAddressKey(right.parent) + spatialAddressKey(right.child));
    }).forEach(function (edge) {
      var parent = spatialEdgePosition(partMap, edge.parent);
      var child = spatialEdgePosition(partMap, edge.child);
      if (!parent || !child) {
        return;
      }
      svg.appendChild(svgNode("line", {
        x1: transform.x(parent[horizontal]), y1: transform.y(parent[vertical]), x2: transform.x(child[horizontal]), y2: transform.y(child[vertical]), class: "preview-containment-edge"
      }));
    });
    preview.joint_edges.slice().sort(function (left, right) {
      return spatialCompare(spatialAddressKey(left.proximal) + spatialAddressKey(left.distal), spatialAddressKey(right.proximal) + spatialAddressKey(right.distal));
    }).forEach(function (edge) {
      var proximal = spatialEdgePosition(partMap, edge.proximal);
      var distal = spatialEdgePosition(partMap, edge.distal);
      if (!proximal || !distal) {
        return;
      }
      svg.appendChild(svgNode("line", {
        x1: transform.x(proximal[horizontal]), y1: transform.y(proximal[vertical]), x2: transform.x(distal[horizontal]), y2: transform.y(distal[vertical]), class: "preview-joint-edge"
      }));
    });
  }

  function spatialDrawParts(svg, transform, parts, horizontal, vertical) {
    var positions = Object.create(null);
    parts.forEach(function (part) {
      var x = Math.round(transform.x(part.position[horizontal]) * 2) / 2;
      var y = Math.round(transform.y(part.position[vertical]) * 2) / 2;
      var key = x + ":" + y;
      var overlap = positions[key] || 0;
      positions[key] = overlap + 1;
      var group = spatialGroup(part.address);
      var color = spatialGroupColor(group);
      var offset = overlap * 11;
      var markerX = x;
      var markerY = y;
      var labelY = y - 9 - offset;
      if (part.placement_source === "authored-attachment") {
        svg.appendChild(svgNode("polygon", {
          points: markerX + "," + (markerY - 9) + " " + (markerX + 9) + "," + markerY + " " + markerX + "," + (markerY + 9) + " " + (markerX - 9) + "," + markerY,
          class: "preview-attachment-marker", stroke: color
        }));
      }
      var marker = svgNode("circle", { cx: markerX, cy: markerY, r: 5.5, class: "preview-part-marker group-" + group, fill: color });
      var markerTitle = svgNode("title");
      markerTitle.textContent = addressText(part.address) + " · exact position [" + part.exact_position.join(", ") + "] · placement source " + part.placement_source;
      marker.appendChild(markerTitle);
      svg.appendChild(marker);
      var label = svgNode("text", { x: markerX + 8, y: labelY, class: "preview-part-label" });
      label.textContent = part.marker_id;
      svg.appendChild(label);
    });
  }

  function spatialPanel(view, normalizedParts, preview, partMap) {
    var panel = node("article", null, "preview-panel");
    panel.appendChild(node("h3", view.title));
    panel.appendChild(node("p", view.description, "preview-panel-description"));
    var svg = svgNode("svg", {
      viewBox: "0 0 420 300", role: "img", class: "preview-svg", "aria-label": view.title + " orthographic primitive placement preview"
    });
    var title = svgNode("title");
    title.textContent = view.title + " primitive placement";
    svg.appendChild(title);
    svg.appendChild(svgNode("rect", { x: 0, y: 0, width: 420, height: 300, class: "preview-background" }));
    var transform = spatialViewTransform(normalizedParts, view.horizontal, view.vertical);
    spatialDrawAxes(svg, transform, view.horizontalLabel, view.verticalLabel);
    spatialDrawEdges(svg, transform, preview, partMap, view.horizontal, view.vertical);
    spatialDrawParts(svg, transform, normalizedParts, view.horizontal, view.vertical);
    panel.appendChild(svg);
    return panel;
  }

  function spatialLegend(preview) {
    var legend = node("div", null, "preview-legend");
    legend.appendChild(node("span", "Legend", "preview-legend-title"));
    [["core", "Core"], ["left", "Left"], ["right", "Right"], ["tail", "Tail / other"]].forEach(function (entry) {
      var item = node("span", null, "preview-legend-item");
      var swatch = node("span", null, "preview-legend-swatch group-" + entry[0]);
      swatch.setAttribute("aria-hidden", "true");
      item.appendChild(swatch);
      item.appendChild(node("span", entry[1]));
      legend.appendChild(item);
    });
    var attachment = node("span", null, "preview-legend-item");
    var attachmentSwatch = node("span", null, "preview-legend-swatch attachment");
    attachmentSwatch.setAttribute("aria-hidden", "true");
    attachment.appendChild(attachmentSwatch);
    attachment.appendChild(node("span", "Attached root"));
    legend.appendChild(attachment);
    var containment = node("span", null, "preview-legend-item");
    var containmentSwatch = node("span", null, "preview-line-swatch containment");
    containment.appendChild(node("span", "Containment"));
    containment.appendChild(containmentSwatch);
    legend.appendChild(containment);
    var joint = node("span", null, "preview-legend-item");
    var jointSwatch = node("span", null, "preview-line-swatch joint");
    joint.appendChild(node("span", "Joint endpoints"));
    joint.appendChild(jointSwatch);
    legend.appendChild(joint);
    if (preview.attachments.length) {
      legend.appendChild(node("span", preview.attachments.length + " attachment provenance record" + (preview.attachments.length === 1 ? "" : "s") + " supplied", "preview-legend-note"));
    }
    return legend;
  }

  function spatialPartKey(parts) {
    var key = node("div", null, "preview-part-key");
    key.appendChild(node("h3", "Part key"));
    key.appendChild(node("p", "In-plot IDs follow sorted semantic Part order. Coordinates are the exact reference positions; source describes how each placement was established.", "preview-part-key-explanation"));
    if (!parts.length) {
      key.appendChild(node("p", "No Parts are present.", "muted"));
      return key;
    }
    var list = node("dl", null, "preview-part-key-list");
    parts.forEach(function (part) {
      var entry = node("div", null, "preview-part-key-entry");
      entry.appendChild(node("dt", part.marker_id));
      var anchors = Array.isArray(part.address.anchors) && part.address.anchors.length ? part.address.anchors.map(String).join(", ") : "none";
      entry.appendChild(node("dd", "role " + String(part.address.role) + " · anchors " + anchors + " · position [" + part.exact_position.join(", ") + "] · source " + part.placement_source));
      list.appendChild(entry);
    });
    key.appendChild(list);
    return key;
  }

  function spatialPreviewSection(structure) {
    if (!isObject(structure) || !Object.prototype.hasOwnProperty.call(structure, "preview")) {
      return null;
    }
    var section = node("section", null, "spatial-preview");
    section.appendChild(node("h2", "Primitive spatial preview"));
    section.appendChild(node("p", "Exact integer Part reference placements shown as a deterministic orthographic guide; Joint frame transforms are not interpreted, and this is not a mesh or runtime view.", "preview-explanation"));
    var validation = spatialPreviewValidation(isObject(structure) ? structure.preview : null);
    if (!validation.valid) {
      var errorPanel = node("div", null, "preview-error");
      errorPanel.appendChild(node("h3", validation.unavailable ? "Preview unavailable" : "Preview could not be rendered"));
      var message = validation.unavailable && isObject(structure.preview.diagnostic) ?
        String(structure.preview.diagnostic.code) + ": " + String(structure.preview.diagnostic.message) :
        validation.errors.slice(0, 2).join(" ");
      errorPanel.appendChild(node("p", message || "The spatial preview payload is malformed."));
      if (validation.errors.length > 2) {
        errorPanel.appendChild(node("p", (validation.errors.length - 2) + " additional preview issue(s) omitted.", "muted"));
      }
      section.appendChild(errorPanel);
      return section;
    }
    var normalizedParts = spatialNormalizedParts(validation.parts);
    var normalizedMap = spatialAddressMap(normalizedParts);
    var panels = node("div", null, "preview-view-grid");
    [
      { title: "Front · x / y", description: "Width and height", horizontal: 0, vertical: 1, horizontalLabel: "x", verticalLabel: "y" },
      { title: "Side · z / y", description: "Depth and height", horizontal: 2, vertical: 1, horizontalLabel: "z", verticalLabel: "y" },
      { title: "Top · x / z", description: "Width and depth", horizontal: 0, vertical: 2, horizontalLabel: "x", verticalLabel: "z" }
    ].forEach(function (view) {
      panels.appendChild(spatialPanel(view, normalizedParts, structure.preview, normalizedMap));
    });
    section.appendChild(panels);
    section.appendChild(spatialPartKey(normalizedParts));
    section.appendChild(spatialLegend(structure.preview));
    var instructions = node("p", "Judge spatial layout, proportions, symmetry, and tail/foot depth. Do not judge mesh, surface, anatomical volume, animation, IK, deformation, or physics.", "preview-instructions");
    section.appendChild(instructions);
    return section;
  }

  var PROVISIONAL_FORM_FORMATS = [
    "creature-kernel.provisional-form-preview.v1",
    "creature-kernel.provisional-form-preview.v2",
    "creature-kernel.provisional-form-preview.v3",
    "creature-kernel.provisional-form-preview.v4",
    "creature-kernel.provisional-form-preview.v5",
    "creature-kernel.provisional-form-preview.v6",
    "creature-kernel.provisional-form-preview.v7",
    "creature-kernel.provisional-form-preview.v8",
    "creature-kernel.provisional-form-preview.v9",
    "creature-kernel.provisional-form-preview.v10"
  ];
  var PROVISIONAL_FORM_V5_FORMAT = "creature-kernel.provisional-form-preview.v5";
  var PROVISIONAL_FORM_V6_FORMAT = "creature-kernel.provisional-form-preview.v6";
  var PROVISIONAL_FORM_V7_FORMAT = "creature-kernel.provisional-form-preview.v7";
  var PROVISIONAL_FORM_V8_FORMAT = "creature-kernel.provisional-form-preview.v8";
  var PROVISIONAL_FORM_V9_FORMAT = "creature-kernel.provisional-form-preview.v9";
  var PROVISIONAL_FORM_V10_FORMAT = "creature-kernel.provisional-form-preview.v10";
  var PROVISIONAL_FORM_TORSO_PROFILE_FORMAT = "creature-kernel.provisional-form-torso-profile.v1";
  var PROVISIONAL_FORM_HEAD_NECK_PROFILE_FORMAT = "creature-kernel.provisional-form-head-neck-profile.v1";
  var PROVISIONAL_FORM_ARM_PROFILE_FORMAT = "creature-kernel.provisional-form-arm-profile.v1";
  var PROVISIONAL_FORM_LEG_PROFILE_FORMAT = "creature-kernel.provisional-form-leg-profile.v1";
  var PROVISIONAL_FORM_SHOULDER_FRAME_ROLE = "form_shoulder_control";
  var PROVISIONAL_FORM_SHOULDER_LANDMARK_ROLES = ["form_shoulder_peak", "form_axilla"];
  var PROVISIONAL_FORM_TORSO_FRAME_ROLE = "form_torso_profile_control";
  var PROVISIONAL_FORM_TORSO_SECTIONS = [
    { name: "lower-pelvis", ownerRole: "pelvis" },
    { name: "upper-pelvis", ownerRole: "pelvis" },
    { name: "lower-abdomen", ownerRole: "torso" },
    { name: "waist-abdomen", ownerRole: "torso" },
    { name: "upper-abdomen", ownerRole: "torso" },
    { name: "lower-ribcage", ownerRole: "torso" },
    { name: "upper-ribcage-shoulder", ownerRole: "torso" }
  ];
  var PROVISIONAL_FORM_TORSO_RADIUS_FACTORS = [
    { name: "lateral", roleSuffix: "lateral_radius" },
    { name: "anterior", roleSuffix: "anterior_radius" },
    { name: "posterior", roleSuffix: "posterior_radius" }
  ];
  var PROVISIONAL_FORM_HEAD_NECK_FRAME_ROLE = "form_head_neck_profile_control";
  var PROVISIONAL_FORM_HEAD_NECK_SECTIONS = [
    { name: "neck-collar", ownerRole: "neck" },
    { name: "neck-upper", ownerRole: "neck" },
    { name: "head-base", ownerRole: "head" },
    { name: "cranium-mid", ownerRole: "head" },
    { name: "cranium-crown", ownerRole: "head" },
    { name: "muzzle-root", ownerRole: "head" },
    { name: "muzzle-mid", ownerRole: "head" },
    { name: "muzzle-tip", ownerRole: "head" }
  ];
  var PROVISIONAL_FORM_HEAD_NECK_RADIUS_FACTORS = [
    { name: "lateral", roleSuffix: "lateral_radius" },
    { name: "up", roleSuffix: "up_radius" },
    { name: "forward", roleSuffix: "forward_radius" }
  ];
  var PROVISIONAL_FORM_HEAD_NECK_CONNECTIONS = [
    { name: "neck-collar-to-neck-upper", from: 0, to: 1, route: "vertical-neck-cranium" },
    { name: "neck-upper-to-head-base", from: 1, to: 2, route: "vertical-neck-cranium" },
    { name: "head-base-to-cranium-mid", from: 2, to: 3, route: "vertical-neck-cranium" },
    { name: "cranium-mid-to-cranium-crown", from: 3, to: 4, route: "vertical-neck-cranium" },
    { name: "cranium-mid-to-muzzle-root", from: 3, to: 5, route: "forward-muzzle" },
    { name: "muzzle-root-to-muzzle-mid", from: 5, to: 6, route: "forward-muzzle" },
    { name: "muzzle-mid-to-muzzle-tip", from: 6, to: 7, route: "forward-muzzle" }
  ];
  var PROVISIONAL_FORM_ARM_FRAME_ROLE = "form_arm_profile_control";
  var PROVISIONAL_FORM_ARM_SIDES = ["left", "right"];
  var PROVISIONAL_FORM_ARM_SECTIONS = [
    { name: "upper-arm-start", ownerRole: "upper_arm" },
    { name: "upper-arm-midpoint", ownerRole: "upper_arm" },
    { name: "elbow", ownerRole: "upper_arm" },
    { name: "forearm-midpoint", ownerRole: "forearm" },
    { name: "forearm-distal", ownerRole: "forearm" }
  ];
  var PROVISIONAL_FORM_ARM_RADIUS_FACTORS = [
    { name: "lateral", roleSuffix: "lateral_radius" },
    { name: "up", roleSuffix: "up_radius" },
    { name: "forward", roleSuffix: "forward_radius" }
  ];
  var PROVISIONAL_FORM_LEG_FRAME_ROLE = "form_leg_profile_control";
  var PROVISIONAL_FORM_LEG_SIDES = ["left", "right"];
  var PROVISIONAL_FORM_LEG_SECTIONS = [
    { name: "thigh-start", ownerRole: "thigh" },
    { name: "thigh-midpoint", ownerRole: "thigh" },
    { name: "knee", ownerRole: "thigh" },
    { name: "shin-midpoint", ownerRole: "shin" },
    { name: "hock-endpoint", ownerRole: "shin" }
  ];
  var PROVISIONAL_FORM_LEG_RADIUS_FACTORS = [
    { name: "lateral", roleSuffix: "lateral_radius" },
    { name: "up", roleSuffix: "up_radius" },
    { name: "forward", roleSuffix: "forward_radius" }
  ];
  var PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE = "source-authored";
  var PROVISIONAL_FORM_VARIANTS = ["neutral-v0", "broad-soft-v0", "lean-readable-v0", "depth-forward-v0"];
  var PROVISIONAL_FORM_VIEWS = [
    { title: "Front · x / y", description: "Width and height", horizontal: 0, vertical: 1, depth: 2, horizontalLabel: "x", verticalLabel: "y" },
    { title: "Side · z / y", description: "Depth and height", horizontal: 2, vertical: 1, depth: 0, horizontalLabel: "z", verticalLabel: "y" },
    { title: "Top · x / z", description: "Width and depth", horizontal: 0, vertical: 2, depth: 1, horizontalLabel: "x", verticalLabel: "z" }
  ];

  function formAddressKey(address) {
    return JSON.stringify([address.namespace, address.anchors, address.kind, address.role]);
  }

  function formDimensionKey(address, role) {
    return JSON.stringify([formAddressKey(address), role]);
  }

  function formDescriptorQualifier(descriptor) {
    var anchors = descriptor && descriptor.address && Array.isArray(descriptor.address.anchors) ? descriptor.address.anchors.map(function (anchor) { return String(anchor).toLowerCase(); }) : [];
    if (anchors.indexOf("left") !== -1 || anchors.indexOf("l") !== -1) { return "left"; }
    if (anchors.indexOf("right") !== -1 || anchors.indexOf("r") !== -1) { return "right"; }
    if (anchors.indexOf("tail") !== -1) { return "tail"; }
    return anchors.length ? anchors.join(", ") : "";
  }

  function formRoleColor(descriptor) {
    var role = descriptor && descriptor.address ? descriptor.address.role : "";
    var qualifier = formDescriptorQualifier(descriptor);
    var text = String(role || "").toLowerCase();
    if (/tail/.test(text)) { return "#ef7ca9"; }
    if (qualifier === "left") { return "#a78bfa"; }
    if (qualifier === "right") { return "#f4a261"; }
    if (/tail/.test(qualifier)) { return "#ef7ca9"; }
    if (/head|neck/.test(text)) { return "#7dd3fc"; }
    if (/hand|foot/.test(text)) { return "#f6c453"; }
    return "#63c6a4";
  }

  function formFiniteVector(value, length) {
    return Array.isArray(value) && value.length === length && value.every(function (component) {
      return typeof component === "number" && isFinite(component);
    });
  }

  function formFiniteI64Vector(value, length) {
    return Array.isArray(value) && value.length === length && value.every(function (component) {
      return typeof component === "number" && isFinite(component) && Number.isInteger(component) && Math.abs(component) <= Math.pow(2, 63) && component !== Math.pow(2, 63);
    });
  }

  function formPositivePermille(value) {
    return typeof value === "number" && isFinite(value) && Number.isInteger(value) && value > 0 && value <= 5000;
  }

  function formGeometryAddress(address) {
    var identifier = /^[a-z][a-z0-9_]*$/;
    return isObject(address) && formHasExactFields(address, ["namespace", "anchors", "kind", "role"]) &&
      typeof address.namespace === "string" && identifier.test(address.namespace) &&
      address.kind === "part" &&
      typeof address.role === "string" && identifier.test(address.role) &&
      Array.isArray(address.anchors) && address.anchors.every(function (anchor) {
        return typeof anchor === "string" && identifier.test(anchor);
      });
  }

  function formDescriptorShape(format, role) {
    var shapes = {
      pelvis: "ellipsoid",
      torso: "ellipsoid",
      neck: "ellipsoid",
      head: "ellipsoid",
      hand: "ellipsoid",
      foot: "ellipsoid",
      upper_arm: "capsule",
      forearm: "capsule",
      thigh: "capsule",
      shin: "capsule",
      tail_root: "tapered-segment",
      tail_tip: "tapered-segment"
    };
    if (role === "neck" && [
      "creature-kernel.provisional-form-preview.v4",
      PROVISIONAL_FORM_V5_FORMAT,
      PROVISIONAL_FORM_V6_FORMAT,
      PROVISIONAL_FORM_V7_FORMAT,
      PROVISIONAL_FORM_V8_FORMAT,
      PROVISIONAL_FORM_V9_FORMAT,
      PROVISIONAL_FORM_V10_FORMAT
    ].indexOf(format) !== -1) {
      return "capsule";
    }
    return Object.prototype.hasOwnProperty.call(shapes, role) ? shapes[role] : null;
  }

  function formCapsuleChildRole(format, role) {
    var childRoles = {
      upper_arm: "forearm",
      forearm: "hand",
      thigh: "shin",
      shin: "foot"
    };
    if (format !== PROVISIONAL_FORM_FORMATS[0] && format !== PROVISIONAL_FORM_FORMATS[1] && format !== PROVISIONAL_FORM_FORMATS[2]) {
      childRoles.neck = "head";
    }
    return Object.prototype.hasOwnProperty.call(childRoles, role) ? childRoles[role] : null;
  }

  function formAddressCompare(left, right) {
    var scalarFields = ["namespace", "kind", "role"];
    if (left.namespace !== right.namespace) { return left.namespace < right.namespace ? -1 : 1; }
    var leftAnchors = left.anchors;
    var rightAnchors = right.anchors;
    for (var index = 0; index < Math.min(leftAnchors.length, rightAnchors.length); index += 1) {
      if (leftAnchors[index] !== rightAnchors[index]) { return leftAnchors[index] < rightAnchors[index] ? -1 : 1; }
    }
    if (leftAnchors.length !== rightAnchors.length) { return leftAnchors.length < rightAnchors.length ? -1 : 1; }
    for (var scalarIndex = 1; scalarIndex < scalarFields.length; scalarIndex += 1) {
      var field = scalarFields[scalarIndex];
      if (left[field] !== right[field]) { return left[field] < right[field] ? -1 : 1; }
    }
    return 0;
  }

  function formVectorEquals(value, expected) {
    return Array.isArray(value) && value.length === expected.length && value.every(function (component, index) {
      return component === expected[index];
    });
  }

  function formControlAddress(address, namespace, side) {
    return isObject(address) && address.namespace === namespace && address.kind === "part" && address.role === "upper_arm" && Array.isArray(address.anchors) && address.anchors.length === 1 && address.anchors[0] === side;
  }

  function formControlSortKey(address, role) {
    return [String(address.namespace), address.anchors.join("\u0001"), String(address.kind), String(address.role), String(role)].join("\u0002");
  }

  function formSafeControlSortKey(address, role) {
    var anchors = isObject(address) && Array.isArray(address.anchors) ? address.anchors.join("\u0001") : "";
    return [String(isObject(address) ? address.namespace : ""), anchors, String(isObject(address) ? address.kind : ""), String(isObject(address) ? address.role : ""), String(role)].join("\u0002");
  }

  function formControlProvenance(provenance, source) {
    return isObject(provenance) && provenance.source === PROVISIONAL_FORM_AUTHORED_CONTROL_PROVENANCE && provenance.document === source.document && provenance.namespace === source.namespace;
  }

  function formV6ShoulderControls(payload) {
    var errors = [];
    var source = payload.source;
    if (typeof source.namespace !== "string" || !source.namespace || typeof source.document !== "string" || !source.document) {
      return ["v6 source identity must provide non-empty namespace and document strings for shoulder controls."];
    }
    var namespace = source.namespace;
    var expectedFrameKeys = {};
    ["left", "right"].forEach(function (side) {
      expectedFrameKeys[formControlSortKey({ namespace: namespace, anchors: [side], kind: "part", role: "upper_arm" }, PROVISIONAL_FORM_SHOULDER_FRAME_ROLE)] = true;
    });
    if (!Array.isArray(payload.authored_frames) || payload.authored_frames.length !== 2) {
      errors.push("v6 authored frames must contain exactly one shoulder control frame per upper arm.");
    } else {
      var seenFrames = {};
      var frameKeys = [];
      payload.authored_frames.forEach(function (frame, index) {
        var where = "v6 authored frame " + index;
        if (!isObject(frame) || !isObject(frame.owner) || typeof frame.role !== "string" || !isObject(frame.transform) || !isObject(frame.provenance)) {
          errors.push(where + " is incomplete.");
          return;
        }
        var side = Array.isArray(frame.owner.anchors) && frame.owner.anchors.length === 1 ? frame.owner.anchors[0] : null;
        if (["left", "right"].indexOf(side) === -1 || !formControlAddress(frame.owner, namespace, side) || frame.role !== PROVISIONAL_FORM_SHOULDER_FRAME_ROLE) {
          errors.push(where + " is not a left/right upper_arm shoulder control frame.");
          return;
        }
        var key = formControlSortKey(frame.owner, frame.role);
        frameKeys.push(key);
        if (seenFrames[key]) { errors.push(where + " duplicates an owner/role key."); }
        seenFrames[key] = true;
        if (!formControlProvenance(frame.provenance, source)) {
          errors.push(where + " provenance is not source-authored for this source.");
        }
        if (!formFiniteVector(frame.transform.translation, 3) || !formVectorEquals(frame.transform.translation, [0, 0, 0]) || !formFiniteVector(frame.transform.rotation_xyzw, 4) || !formVectorEquals(frame.transform.rotation_xyzw, [0, 0, 0, 1])) {
          errors.push(where + " must use the identity rigid transform.");
        }
      });
      if (Object.keys(seenFrames).length !== 2 || Object.keys(expectedFrameKeys).some(function (key) { return !seenFrames[key]; })) {
        errors.push("v6 authored frames must contain exactly the left/right upper_arm shoulder control inventory.");
      }
      if (frameKeys.some(function (key, index) { return index > 0 && key < frameKeys[index - 1]; })) {
        errors.push("v6 authored frames must use stable owner/role order.");
      }
    }

    var expectedLandmarkKeys = {};
    ["left", "right"].forEach(function (side) {
      PROVISIONAL_FORM_SHOULDER_LANDMARK_ROLES.forEach(function (role) {
        expectedLandmarkKeys[formControlSortKey({ namespace: namespace, anchors: [side], kind: "part", role: "upper_arm" }, role)] = true;
      });
    });
    if (!Array.isArray(payload.authored_landmarks) || payload.authored_landmarks.length !== 4) {
      errors.push("v6 authored landmarks must contain exactly peak and axilla per upper arm.");
    } else {
      var seenLandmarks = {};
      var landmarkKeys = [];
      payload.authored_landmarks.forEach(function (landmark, index) {
        var where = "v6 authored landmark " + index;
        if (!isObject(landmark) || !isObject(landmark.owner) || typeof landmark.role !== "string" || !isObject(landmark.frame) || !isObject(landmark.provenance)) {
          errors.push(where + " is incomplete.");
          return;
        }
        var side = Array.isArray(landmark.owner.anchors) && landmark.owner.anchors.length === 1 ? landmark.owner.anchors[0] : null;
        if (["left", "right"].indexOf(side) === -1 || !formControlAddress(landmark.owner, namespace, side) || PROVISIONAL_FORM_SHOULDER_LANDMARK_ROLES.indexOf(landmark.role) === -1) {
          errors.push(where + " is not a peak or axilla landmark on a left/right upper_arm.");
          return;
        }
        var key = formControlSortKey(landmark.owner, landmark.role);
        landmarkKeys.push(key);
        if (seenLandmarks[key]) { errors.push(where + " duplicates an owner/role key."); }
        seenLandmarks[key] = true;
        if (!isObject(landmark.frame) || !formControlAddress(landmark.frame.owner, namespace, side) || !formControlAddress(landmark.owner, namespace, side) || landmark.frame.owner.namespace !== landmark.owner.namespace || JSON.stringify(landmark.frame.owner.anchors) !== JSON.stringify(landmark.owner.anchors) || landmark.frame.owner.kind !== landmark.owner.kind || landmark.frame.owner.role !== landmark.owner.role || landmark.frame.role !== PROVISIONAL_FORM_SHOULDER_FRAME_ROLE) {
          errors.push(where + " frame must reference its same-owner shoulder control frame.");
        }
        if (!formFiniteVector(landmark.position, 3) || landmark.position.some(function (component) { return Math.abs(component) > 1.0; })) {
          errors.push(where + " position must be finite and within +/-1.0.");
        }
        if (!formControlProvenance(landmark.provenance, source)) {
          errors.push(where + " provenance is not source-authored for this source.");
        }
      });
      if (Object.keys(seenLandmarks).length !== 4 || Object.keys(expectedLandmarkKeys).some(function (key) { return !seenLandmarks[key]; })) {
        errors.push("v6 authored landmarks must contain exactly peak and axilla for both upper arms.");
      }
      if (landmarkKeys.some(function (key, index) { return index > 0 && key < landmarkKeys[index - 1]; })) {
        errors.push("v6 authored landmarks must use stable owner/role order.");
      }
    }
    return errors;
  }

  function formHasExactFields(value, expected) {
    if (!isObject(value)) { return false; }
    var actual = Object.keys(value).sort();
    var required = expected.slice().sort();
    return actual.length === required.length && actual.every(function (key, index) {
      return key === required[index];
    });
  }

  function formAddressEquals(left, right) {
    return isObject(left) && isObject(right) &&
      left.namespace === right.namespace && left.kind === right.kind && left.role === right.role &&
      Array.isArray(left.anchors) && Array.isArray(right.anchors) &&
      JSON.stringify(left.anchors) === JSON.stringify(right.anchors);
  }

  function formTorsoOwner(namespace, role) {
    return { namespace: namespace, anchors: [], kind: "part", role: role };
  }

  function formV7AuthoredTorsoProfile(payload, includeV8Controls, includeV9Controls, includeV10Controls) {
    var errors = [];
    var dimensionKeys = {};
    var sourceSections = [];
    var source = payload.source;
    if (!formHasExactFields(source, ["document", "namespace", "resource_profile_id"]) || typeof source.namespace !== "string" || !source.namespace || typeof source.document !== "string" || !source.document || source.resource_profile_id !== "ck.resource.body.r2") {
      return { errors: ["v7 source identity must provide non-empty namespace and document strings for torso controls."], dimensionKeys: dimensionKeys, sourceSections: sourceSections };
    }
    var namespace = source.namespace;
    var frames = Array.isArray(payload.authored_frames) ? payload.authored_frames : [];
    var landmarks = Array.isArray(payload.authored_landmarks) ? payload.authored_landmarks : [];
    var shoulderFrames = frames.filter(function (item) { return isObject(item) && item.role === PROVISIONAL_FORM_SHOULDER_FRAME_ROLE; });
    var shoulderLandmarks = landmarks.filter(function (item) { return isObject(item) && PROVISIONAL_FORM_SHOULDER_LANDMARK_ROLES.indexOf(item.role) !== -1; });
    formV6ShoulderControls({ source: source, authored_frames: shoulderFrames, authored_landmarks: shoulderLandmarks }).forEach(function (error) {
      errors.push(error);
    });

    var expectedFrameKeys = {};
    ["left", "right"].forEach(function (side) {
      var owner = { namespace: namespace, anchors: [side], kind: "part", role: "upper_arm" };
      expectedFrameKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, PROVISIONAL_FORM_SHOULDER_FRAME_ROLE])] = true;
    });
    ["pelvis", "torso"].forEach(function (role) {
      var owner = formTorsoOwner(namespace, role);
      expectedFrameKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, PROVISIONAL_FORM_TORSO_FRAME_ROLE])] = true;
    });
    if (includeV8Controls) {
      ["neck", "head"].forEach(function (role) {
        var owner = formHeadNeckOwner(namespace, role);
        expectedFrameKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, PROVISIONAL_FORM_HEAD_NECK_FRAME_ROLE])] = true;
      });
    }
    if (includeV9Controls) {
      PROVISIONAL_FORM_ARM_SIDES.forEach(function (side) {
        ["upper_arm", "forearm"].forEach(function (role) {
          var owner = formArmOwner(namespace, side, role);
          expectedFrameKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, PROVISIONAL_FORM_ARM_FRAME_ROLE])] = true;
        });
      });
    }
    if (includeV10Controls) {
      PROVISIONAL_FORM_LEG_SIDES.forEach(function (side) {
        ["thigh", "shin"].forEach(function (role) {
          var owner = formLegOwner(namespace, side, role);
          expectedFrameKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, PROVISIONAL_FORM_LEG_FRAME_ROLE])] = true;
        });
      });
    }
    var contractLabel = includeV10Controls ? "v10" : includeV9Controls ? "v9" : includeV8Controls ? "v8" : "v7";
    var expectedFrameCount = includeV10Controls ? 14 : includeV9Controls ? 10 : includeV8Controls ? 6 : 4;
    var frameMap = {};
    var frameOrder = [];
    if (frames.length !== expectedFrameCount) {
      errors.push(contractLabel + " authored frames must contain exactly " + expectedFrameCount + " control frames.");
    }
    frames.forEach(function (frame, index) {
      var where = "v7 authored frame " + index;
      if (!formHasExactFields(frame, ["owner", "role", "transform", "provenance"]) || !formHasExactFields(frame.owner, ["namespace", "anchors", "kind", "role"]) || typeof frame.role !== "string" || !isObject(frame.transform) || !isObject(frame.provenance)) {
        errors.push(where + " is incomplete or has unknown fields.");
        return;
      }
      var key = JSON.stringify([frame.owner.namespace, frame.owner.anchors, frame.owner.kind, frame.owner.role, frame.role]);
      if (!expectedFrameKeys[key]) { errors.push(where + " is not a " + contractLabel + " control frame."); }
      if (frameMap[key]) { errors.push(where + " duplicates an owner/role key."); }
      frameMap[key] = frame;
      frameOrder.push(formSafeControlSortKey(frame.owner, frame.role));
      if (!formControlProvenance(frame.provenance, source) || !formHasExactFields(frame.provenance, ["source", "document", "namespace"])) {
        errors.push(where + " provenance is not exact source-authored provenance.");
      }
      if (!formHasExactFields(frame.transform, ["translation", "rotation_xyzw"]) || !formFiniteVector(frame.transform.translation, 3) || !formVectorEquals(frame.transform.translation, [0, 0, 0]) || !formFiniteVector(frame.transform.rotation_xyzw, 4) || !formVectorEquals(frame.transform.rotation_xyzw, [0, 0, 0, 1])) {
        errors.push(where + " must use the identity rigid transform.");
      }
    });
    if (Object.keys(frameMap).length !== Object.keys(expectedFrameKeys).length || Object.keys(expectedFrameKeys).some(function (key) { return !frameMap[key]; })) {
      errors.push(contractLabel + " authored frames must contain the exact control inventory.");
    }
    if (frameOrder.some(function (key, index) { return index > 0 && key < frameOrder[index - 1]; })) {
      errors.push("v7 authored frames must use stable owner/role order.");
    }

    var expectedLandmarkKeys = {};
    ["left", "right"].forEach(function (side) {
      var owner = { namespace: namespace, anchors: [side], kind: "part", role: "upper_arm" };
      PROVISIONAL_FORM_SHOULDER_LANDMARK_ROLES.forEach(function (role) {
        expectedLandmarkKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, role])] = true;
      });
    });
    PROVISIONAL_FORM_TORSO_SECTIONS.forEach(function (section) {
      var owner = formTorsoOwner(namespace, section.ownerRole);
      var role = "form_torso_profile_" + section.name.replace(/-/g, "_");
      expectedLandmarkKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, role])] = true;
    });
    if (includeV8Controls) {
      PROVISIONAL_FORM_HEAD_NECK_SECTIONS.forEach(function (section) {
        var owner = formHeadNeckOwner(namespace, section.ownerRole);
        var role = "form_head_neck_profile_" + section.name.replace(/-/g, "_");
        expectedLandmarkKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, role])] = true;
      });
    }
    if (includeV9Controls) {
      PROVISIONAL_FORM_ARM_SIDES.forEach(function (side) {
        PROVISIONAL_FORM_ARM_SECTIONS.forEach(function (section) {
          var owner = formArmOwner(namespace, side, section.ownerRole);
          var role = "form_arm_profile_" + section.name.replace(/-/g, "_");
          expectedLandmarkKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, role])] = true;
        });
      });
    }
    if (includeV10Controls) {
      PROVISIONAL_FORM_LEG_SIDES.forEach(function (side) {
        PROVISIONAL_FORM_LEG_SECTIONS.forEach(function (section) {
          var owner = formLegOwner(namespace, side, section.ownerRole);
          var role = "form_leg_profile_" + section.name.replace(/-/g, "_");
          expectedLandmarkKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, role])] = true;
        });
      });
    }
    var expectedLandmarkCount = includeV10Controls ? 39 : includeV9Controls ? 29 : includeV8Controls ? 19 : 11;
    var landmarkMap = {};
    var landmarkOrder = [];
    if (landmarks.length !== expectedLandmarkCount) {
      errors.push(contractLabel + " authored landmarks must contain exactly " + expectedLandmarkCount + " control landmarks.");
    }
    landmarks.forEach(function (landmark, index) {
      var where = "v7 authored landmark " + index;
      if (!formHasExactFields(landmark, ["owner", "role", "frame", "position", "provenance"]) || !formHasExactFields(landmark.owner, ["namespace", "anchors", "kind", "role"]) || typeof landmark.role !== "string" || !isObject(landmark.frame) || !formHasExactFields(landmark.frame.owner, ["namespace", "anchors", "kind", "role"]) || !isObject(landmark.provenance)) {
        errors.push(where + " is incomplete or has unknown fields.");
        return;
      }
      var key = JSON.stringify([landmark.owner.namespace, landmark.owner.anchors, landmark.owner.kind, landmark.owner.role, landmark.role]);
      if (!expectedLandmarkKeys[key]) { errors.push(where + " is not a " + contractLabel + " control landmark."); }
      if (landmarkMap[key]) { errors.push(where + " duplicates an owner/role key."); }
      landmarkMap[key] = landmark;
      landmarkOrder.push(formSafeControlSortKey(landmark.owner, landmark.role));
      if (!formControlProvenance(landmark.provenance, source) || !formHasExactFields(landmark.provenance, ["source", "document", "namespace"])) {
        errors.push(where + " provenance is not exact source-authored provenance.");
      }
      var isTorsoLandmark = landmark.owner.role === "pelvis" || landmark.owner.role === "torso";
      var expectedFrameRole = includeV9Controls && landmark.role.indexOf("form_arm_profile_") === 0 ? PROVISIONAL_FORM_ARM_FRAME_ROLE : includeV10Controls && landmark.role.indexOf("form_leg_profile_") === 0 ? PROVISIONAL_FORM_LEG_FRAME_ROLE : isTorsoLandmark ? PROVISIONAL_FORM_TORSO_FRAME_ROLE : includeV8Controls && (landmark.owner.role === "neck" || landmark.owner.role === "head") ? PROVISIONAL_FORM_HEAD_NECK_FRAME_ROLE : PROVISIONAL_FORM_SHOULDER_FRAME_ROLE;
      if (!formHasExactFields(landmark.frame, ["owner", "role"]) || !formAddressEquals(landmark.frame.owner, landmark.owner) || landmark.frame.role !== expectedFrameRole) {
        errors.push(where + " frame must reference its same-owner control frame.");
      }
      var frameKey = isObject(landmark.frame.owner) ? JSON.stringify([landmark.frame.owner.namespace, landmark.frame.owner.anchors, landmark.frame.owner.kind, landmark.frame.owner.role, landmark.frame.role]) : "";
      if (!frameMap[frameKey]) { errors.push(where + " frame references an unlisted authored frame."); }
      if (!formFiniteVector(landmark.position, 3) || landmark.position.some(function (component) { return Math.abs(component) > 1.0; })) {
        errors.push(where + " position must be finite and within +/-1.0.");
      }
      if (isTorsoLandmark && (!formFiniteVector(landmark.position, 3) || landmark.position[0] !== 0 || landmark.position[2] !== 0)) {
        errors.push(where + " position must be an axial [0,y,0] point.");
      }
      if (includeV8Controls && (landmark.owner.role === "neck" || landmark.owner.role === "head") && (!formFiniteVector(landmark.position, 3) || landmark.position[0] !== 0)) {
        errors.push(where + " position must be an axial [0,y,z] point.");
      }
      if (includeV9Controls && landmark.role.indexOf("form_arm_profile_") === 0 && (!formFiniteVector(landmark.position, 3) || landmark.owner.role !== "upper_arm" && landmark.owner.role !== "forearm" || landmark.position[0] !== 0 || landmark.position[2] !== 0)) {
        errors.push(where + " position must be an axial [0,y,0] point.");
      }
      if (includeV10Controls && landmark.role.indexOf("form_leg_profile_") === 0 && (!formFiniteVector(landmark.position, 3) || landmark.owner.role !== "thigh" && landmark.owner.role !== "shin" || landmark.position[0] !== 0 || landmark.position[2] !== 0)) {
        errors.push(where + " position must be an axial [0,y,0] point.");
      }
      if (includeV10Controls && landmark.role.indexOf("form_leg_profile_") === 0 && (!formFiniteVector(landmark.position, 3) || landmark.position[1] < -1.0 || landmark.position[1] > 0.0)) {
        errors.push(where + " position y must be in inclusive [-1.0, 0.0].");
      }
    });
    if (Object.keys(landmarkMap).length !== Object.keys(expectedLandmarkKeys).length || Object.keys(expectedLandmarkKeys).some(function (key) { return !landmarkMap[key]; })) {
      errors.push(contractLabel + " authored landmarks must contain the exact control inventory.");
    }
    if (landmarkOrder.some(function (key, index) { return index > 0 && key < landmarkOrder[index - 1]; })) {
      errors.push("v7 authored landmarks must use stable owner/role order.");
    }

    var dimensions = Array.isArray(payload.authored_dimensions) ? payload.authored_dimensions : [];
    var dimensionMap = {};
    var dimensionOrder = [];
    dimensions.forEach(function (dimension, index) {
      var where = "v7 authored dimension " + index;
      if (!formHasExactFields(dimension, ["owner", "role", "value_permille", "provenance"]) || !formHasExactFields(dimension.owner, ["namespace", "anchors", "kind", "role"]) || typeof dimension.role !== "string" || !isObject(dimension.provenance) || !Number.isInteger(dimension.value_permille) || dimension.value_permille <= 0 || dimension.value_permille > 5000) {
        errors.push(where + " is incomplete, unknown, or outside the positive permille bound.");
        return;
      }
      var key = formDimensionKey(dimension.owner, dimension.role);
      if (dimensionMap[key]) { errors.push(where + " duplicates an owner/role key."); }
      dimensionMap[key] = dimension;
      dimensionOrder.push(formSafeControlSortKey(dimension.owner, dimension.role));
      if (dimension.owner.namespace !== namespace || !formControlProvenance(dimension.provenance, source) || !formHasExactFields(dimension.provenance, ["source", "document", "namespace"])) {
        errors.push(where + " has invalid source provenance or namespace.");
      }
    });
    if (dimensionOrder.some(function (key, index) { return index > 0 && key < dimensionOrder[index - 1]; })) {
      errors.push("v7 authored dimensions must use stable owner/role order.");
    }

    var profile = payload.authored_torso_profile;
    if (!formHasExactFields(profile, ["format", "provenance", "sections"]) || profile.format !== PROVISIONAL_FORM_TORSO_PROFILE_FORMAT || !formControlProvenance(profile.provenance, source) || !formHasExactFields(profile.provenance, ["source", "document", "namespace"]) || !Array.isArray(profile.sections)) {
      errors.push("v7 authored_torso_profile has an unexpected format or fields.");
      return { errors: errors, dimensionKeys: dimensionKeys, sourceSections: sourceSections };
    }
    if (profile.sections.length !== PROVISIONAL_FORM_TORSO_SECTIONS.length) {
      errors.push("v7 authored_torso_profile must contain exactly seven sections.");
    }
    var sectionY = [];
    PROVISIONAL_FORM_TORSO_SECTIONS.forEach(function (expected, index) {
      var section = profile.sections[index];
      var where = "v7 torso profile section " + index;
      var sourceSection = { name: expected.name, ownerRole: expected.ownerRole, position: null, radii: {} };
      sourceSections.push(sourceSection);
      if (!formHasExactFields(section, ["name", "frame_index", "landmark_index", "dimension_indices", "provenance", "section_index"]) || !isObject(section.dimension_indices) || !formControlProvenance(section.provenance, source) || !formHasExactFields(section.provenance, ["source", "document", "namespace"])) {
        errors.push(where + " is incomplete or has unknown fields.");
        return;
      }
      if (section.name !== expected.name) { errors.push(where + " is not in the required stable order."); }
      if (!Number.isInteger(section.section_index) || section.section_index !== index) {
        errors.push(where + " section_index must equal its stable array index.");
      }
      var owner = formTorsoOwner(namespace, expected.ownerRole);
      if (!Number.isInteger(section.frame_index) || section.frame_index < 0 || section.frame_index >= frames.length) {
        errors.push(where + " frame_index must be an in-range integer index.");
      } else {
        var indexedFrame = frames[section.frame_index];
        if (!isObject(indexedFrame) || !formAddressEquals(indexedFrame.owner, owner) || indexedFrame.role !== PROVISIONAL_FORM_TORSO_FRAME_ROLE) {
          errors.push(where + " frame_index does not resolve to its identity owner torso control frame.");
        }
      }
      var sectionKey = expected.name.replace(/-/g, "_");
      var landmarkRole = "form_torso_profile_" + sectionKey;
      if (!Number.isInteger(section.landmark_index) || section.landmark_index < 0 || section.landmark_index >= landmarks.length) {
        errors.push(where + " landmark_index must be an in-range integer index.");
      } else {
        var indexedLandmark = landmarks[section.landmark_index];
        if (!isObject(indexedLandmark) || !formAddressEquals(indexedLandmark.owner, owner) || indexedLandmark.role !== landmarkRole) {
          errors.push(where + " landmark_index does not resolve to the canonical axial landmark.");
        } else if (formFiniteVector(indexedLandmark.position, 3)) {
          sourceSection.position = indexedLandmark.position.slice();
          sectionY.push(indexedLandmark.position[1]);
        }
      }
      if (!formHasExactFields(section.dimension_indices, ["lateral", "anterior", "posterior"])) {
        errors.push(where + " dimension_indices must contain exactly lateral, anterior, and posterior.");
        return;
      }
      PROVISIONAL_FORM_TORSO_RADIUS_FACTORS.forEach(function (factor) {
        var dimensionIndex = section.dimension_indices[factor.name];
        var role = "form_torso_profile_" + sectionKey + "_" + factor.roleSuffix;
        if (!Number.isInteger(dimensionIndex) || dimensionIndex < 0 || dimensionIndex >= dimensions.length) {
          errors.push(where + " dimension_indices." + factor.name + " must be an in-range integer index.");
          return;
        }
        var indexedDimension = dimensions[dimensionIndex];
        if (!isObject(indexedDimension) || !formAddressEquals(indexedDimension.owner, owner) || indexedDimension.role !== role) {
          errors.push(where + " dimension_indices." + factor.name + " does not resolve to " + role + ".");
          return;
        }
        var key = formDimensionKey(indexedDimension.owner, indexedDimension.role);
        dimensionKeys[key] = true;
        sourceSection.radii[factor.name] = indexedDimension.value_permille;
      });
    });
    if (sectionY.some(function (value, index) { return index > 0 && value <= sectionY[index - 1]; })) {
      errors.push("v7 torso profile landmarks must have strictly increasing y.");
    }
    return { errors: errors, dimensionKeys: dimensionKeys, sourceSections: sourceSections };
  }

  function formTorsoProfileFactors(profileId, ownerRole) {
    if (profileId === "neutral-v0") { return { lateral: 1000, depth: 1000 }; }
    if (profileId === "broad-soft-v0" && (ownerRole === "pelvis" || ownerRole === "torso")) { return { lateral: 1200, depth: 1150 }; }
    if (profileId === "lean-readable-v0") { return { lateral: 800, depth: 800 }; }
    if (profileId === "depth-forward-v0" && ownerRole === "torso") { return { lateral: 1000, depth: 1300 }; }
    return { lateral: 1000, depth: 1000 };
  }

  function formV7VariantTorsoProfile(profile, profileId, source, sourceSections) {
    var errors = [];
    var prefix = "Variant " + profileId + " torso_profile";
    if (!formHasExactFields(profile, ["format", "source", "provenance", "sections"]) || profile.format !== PROVISIONAL_FORM_TORSO_PROFILE_FORMAT || profile.source !== "authored_torso_profile" || !formControlProvenance(profile.provenance, source) || !formHasExactFields(profile.provenance, ["source", "document", "namespace"]) || !Array.isArray(profile.sections)) {
      return [prefix + " has an unexpected format, source, provenance, or fields."];
    }
    if (profile.sections.length !== PROVISIONAL_FORM_TORSO_SECTIONS.length || sourceSections.length !== PROVISIONAL_FORM_TORSO_SECTIONS.length) {
      errors.push(prefix + " must contain exactly seven source-indexed sections.");
      return errors;
    }
    profile.sections.forEach(function (section, index) {
      var where = prefix + " section " + index;
      var sourceSection = sourceSections[index];
      if (!formHasExactFields(section, ["source_section_index", "name", "position", "lateral_radius_permille", "anterior_radius_permille", "posterior_radius_permille", "scaling", "provenance"]) || !isObject(sourceSection) || !isObject(section.scaling) || !formControlProvenance(section.provenance, source) || !formHasExactFields(section.provenance, ["source", "document", "namespace"])) {
        errors.push(where + " is incomplete or has unknown fields.");
        return;
      }
      if (!Number.isInteger(section.source_section_index) || section.source_section_index !== index) {
        errors.push(where + " source_section_index must equal its stable source index.");
      }
      if (section.name !== sourceSection.name) {
        errors.push(where + " name does not match its indexed source section.");
      }
      if (!formFiniteVector(section.position, 3) || !Array.isArray(sourceSection.position) || !formVectorEquals(section.position, sourceSection.position)) {
        errors.push(where + " position must equal its indexed source landmark.");
      }
      var factors = formTorsoProfileFactors(profileId, sourceSection.ownerRole);
      var expectedScaling = {
        lateral_factor_permille: factors.lateral,
        anterior_factor_permille: factors.depth,
        posterior_factor_permille: factors.depth
      };
      if (!formHasExactFields(section.scaling, Object.keys(expectedScaling))) {
        errors.push(where + " scaling must contain exactly the three axis factors.");
      } else {
        Object.keys(expectedScaling).forEach(function (field) {
          if (!Number.isInteger(section.scaling[field]) || section.scaling[field] <= 0 || section.scaling[field] > 5000 || section.scaling[field] !== expectedScaling[field]) {
            errors.push(where + " " + field + " does not match the fixed variant factor.");
          }
        });
      }
      PROVISIONAL_FORM_TORSO_RADIUS_FACTORS.forEach(function (factor) {
        var field = factor.name + "_radius_permille";
        var axisFactor = factor.name === "lateral" ? factors.lateral : factors.depth;
        var sourceRadius = sourceSection.radii[factor.name];
        var expectedRadius = Number.isInteger(sourceRadius) ? Math.floor(sourceRadius * axisFactor / 1000) : NaN;
        if (!Number.isInteger(section[field]) || section[field] <= 0 || section[field] > 5000 || section[field] !== expectedRadius) {
          errors.push(where + " " + field + " does not match its indexed source radius and fixed factor.");
        }
      });
    });
    return errors;
  }

  function formHeadNeckOwner(namespace, role) {
    return { namespace: namespace, anchors: [], kind: "part", role: role };
  }

  function formArmOwner(namespace, side, role) {
    return { namespace: namespace, anchors: [side], kind: "part", role: role };
  }

  function formLegOwner(namespace, side, role) {
    return { namespace: namespace, anchors: [side], kind: "part", role: role };
  }

  function formHeadNeckProfileFactors(profileId, ownerRole) {
    if (ownerRole === "head") {
      if (profileId === "neutral-v0") { return { lateral: 1000, up: 1000, forward: 1000 }; }
      if (profileId === "broad-soft-v0") { return { lateral: 1200, up: 1000, forward: 1150 }; }
      if (profileId === "lean-readable-v0") { return { lateral: 800, up: 1000, forward: 800 }; }
      if (profileId === "depth-forward-v0") { return { lateral: 1000, up: 1000, forward: 1300 }; }
      return { lateral: 1000, up: 1000, forward: 1000 };
    }
    var factor = profileId === "broad-soft-v0" ? 1150 : profileId === "lean-readable-v0" ? 800 : 1000;
    return { lateral: factor, up: factor, forward: factor };
  }

  function formV8AuthoredHeadNeckProfile(payload, includeV9Controls, includeV10Controls) {
    var errors = [];
    var dimensionKeys = {};
    var sourceSections = [];
    var source = payload.source;
    if (!formHasExactFields(source, ["document", "namespace", "resource_profile_id"]) || typeof source.namespace !== "string" || !source.namespace || typeof source.document !== "string" || !source.document || source.resource_profile_id !== "ck.resource.body.r2") {
      return { errors: ["v8 source identity must provide non-empty namespace and document strings for head/neck controls."], dimensionKeys: dimensionKeys, sourceSections: sourceSections };
    }
    var namespace = source.namespace;
    var frames = Array.isArray(payload.authored_frames) ? payload.authored_frames : [];
    var expectedFrameKeys = {};
    ["left", "right"].forEach(function (side) {
      var owner = { namespace: namespace, anchors: [side], kind: "part", role: "upper_arm" };
      expectedFrameKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, PROVISIONAL_FORM_SHOULDER_FRAME_ROLE])] = true;
    });
    ["pelvis", "torso"].forEach(function (role) {
      var owner = formTorsoOwner(namespace, role);
      expectedFrameKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, PROVISIONAL_FORM_TORSO_FRAME_ROLE])] = true;
    });
    ["neck", "head"].forEach(function (role) {
      var owner = formHeadNeckOwner(namespace, role);
      expectedFrameKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, PROVISIONAL_FORM_HEAD_NECK_FRAME_ROLE])] = true;
    });
    if (includeV9Controls) {
      PROVISIONAL_FORM_ARM_SIDES.forEach(function (side) {
        ["upper_arm", "forearm"].forEach(function (role) {
          var owner = formArmOwner(namespace, side, role);
          expectedFrameKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, PROVISIONAL_FORM_ARM_FRAME_ROLE])] = true;
        });
      });
    }
    if (includeV10Controls) {
      PROVISIONAL_FORM_LEG_SIDES.forEach(function (side) {
        ["thigh", "shin"].forEach(function (role) {
          var owner = formLegOwner(namespace, side, role);
          expectedFrameKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, PROVISIONAL_FORM_LEG_FRAME_ROLE])] = true;
        });
      });
    }
    var contractLabel = includeV10Controls ? "v10" : includeV9Controls ? "v9" : "v8";
    var expectedFrameCount = includeV10Controls ? 14 : includeV9Controls ? 10 : 6;
    var frameMap = {};
    var frameOrder = [];
    if (frames.length !== expectedFrameCount) { errors.push(contractLabel + " authored frames must contain exactly " + expectedFrameCount + " control frames."); }
    frames.forEach(function (frame, index) {
      var where = "v8 authored frame " + index;
      if (!formHasExactFields(frame, ["owner", "role", "transform", "provenance"]) || !formHasExactFields(frame.owner, ["namespace", "anchors", "kind", "role"]) || typeof frame.role !== "string" || !isObject(frame.transform) || !isObject(frame.provenance)) {
        errors.push(where + " is incomplete or has unknown fields.");
        return;
      }
      var key = JSON.stringify([frame.owner.namespace, frame.owner.anchors, frame.owner.kind, frame.owner.role, frame.role]);
      if (!expectedFrameKeys[key]) { errors.push(where + " is not a " + contractLabel + " control frame."); }
      if (frameMap[key]) { errors.push(where + " duplicates an owner/role key."); }
      frameMap[key] = frame;
      frameOrder.push(formSafeControlSortKey(frame.owner, frame.role));
      if (!formControlProvenance(frame.provenance, source) || !formHasExactFields(frame.provenance, ["source", "document", "namespace"])) {
        errors.push(where + " provenance is not exact source-authored provenance.");
      }
      if (!formHasExactFields(frame.transform, ["translation", "rotation_xyzw"]) || !formFiniteVector(frame.transform.translation, 3) || !formVectorEquals(frame.transform.translation, [0, 0, 0]) || !formFiniteVector(frame.transform.rotation_xyzw, 4) || !formVectorEquals(frame.transform.rotation_xyzw, [0, 0, 0, 1])) {
        errors.push(where + " must use the identity rigid transform.");
      }
    });
    if (Object.keys(frameMap).length !== Object.keys(expectedFrameKeys).length || Object.keys(expectedFrameKeys).some(function (key) { return !frameMap[key]; })) {
      errors.push(contractLabel + " authored frames must contain the exact control inventory.");
    }
    if (frameOrder.some(function (key, index) { return index > 0 && key < frameOrder[index - 1]; })) {
      errors.push("v8 authored frames must use stable owner/role order.");
    }

    var landmarks = Array.isArray(payload.authored_landmarks) ? payload.authored_landmarks : [];
    var expectedLandmarkKeys = {};
    ["left", "right"].forEach(function (side) {
      var owner = { namespace: namespace, anchors: [side], kind: "part", role: "upper_arm" };
      PROVISIONAL_FORM_SHOULDER_LANDMARK_ROLES.forEach(function (role) {
        expectedLandmarkKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, role])] = true;
      });
    });
    PROVISIONAL_FORM_TORSO_SECTIONS.forEach(function (section) {
      var owner = formTorsoOwner(namespace, section.ownerRole);
      var role = "form_torso_profile_" + section.name.replace(/-/g, "_");
      expectedLandmarkKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, role])] = true;
    });
    PROVISIONAL_FORM_HEAD_NECK_SECTIONS.forEach(function (section) {
      var owner = formHeadNeckOwner(namespace, section.ownerRole);
      var role = "form_head_neck_profile_" + section.name.replace(/-/g, "_");
      expectedLandmarkKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, role])] = true;
    });
    if (includeV9Controls) {
      PROVISIONAL_FORM_ARM_SIDES.forEach(function (side) {
        PROVISIONAL_FORM_ARM_SECTIONS.forEach(function (section) {
          var owner = formArmOwner(namespace, side, section.ownerRole);
          var role = "form_arm_profile_" + section.name.replace(/-/g, "_");
          expectedLandmarkKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, role])] = true;
        });
      });
    }
    if (includeV10Controls) {
      PROVISIONAL_FORM_LEG_SIDES.forEach(function (side) {
        PROVISIONAL_FORM_LEG_SECTIONS.forEach(function (section) {
          var owner = formLegOwner(namespace, side, section.ownerRole);
          var role = "form_leg_profile_" + section.name.replace(/-/g, "_");
          expectedLandmarkKeys[JSON.stringify([owner.namespace, owner.anchors, owner.kind, owner.role, role])] = true;
        });
      });
    }
    var expectedLandmarkCount = includeV10Controls ? 39 : includeV9Controls ? 29 : 19;
    var landmarkMap = {};
    var landmarkOrder = [];
    if (landmarks.length !== expectedLandmarkCount) { errors.push(contractLabel + " authored landmarks must contain exactly " + expectedLandmarkCount + " control landmarks."); }
    landmarks.forEach(function (landmark, index) {
      var where = "v8 authored landmark " + index;
      if (!formHasExactFields(landmark, ["owner", "role", "frame", "position", "provenance"]) || !formHasExactFields(landmark.owner, ["namespace", "anchors", "kind", "role"]) || typeof landmark.role !== "string" || !isObject(landmark.frame) || !formHasExactFields(landmark.frame.owner, ["namespace", "anchors", "kind", "role"]) || !isObject(landmark.provenance)) {
        errors.push(where + " is incomplete or has unknown fields.");
        return;
      }
      var key = JSON.stringify([landmark.owner.namespace, landmark.owner.anchors, landmark.owner.kind, landmark.owner.role, landmark.role]);
      if (!expectedLandmarkKeys[key]) { errors.push(where + " is not a " + contractLabel + " control landmark."); }
      if (landmarkMap[key]) { errors.push(where + " duplicates an owner/role key."); }
      landmarkMap[key] = landmark;
      landmarkOrder.push(formSafeControlSortKey(landmark.owner, landmark.role));
      if (!formControlProvenance(landmark.provenance, source) || !formHasExactFields(landmark.provenance, ["source", "document", "namespace"])) {
        errors.push(where + " provenance is not exact source-authored provenance.");
      }
      var expectedFrameRole = includeV9Controls && landmark.role.indexOf("form_arm_profile_") === 0 ? PROVISIONAL_FORM_ARM_FRAME_ROLE : includeV10Controls && landmark.role.indexOf("form_leg_profile_") === 0 ? PROVISIONAL_FORM_LEG_FRAME_ROLE : landmark.owner.role === "pelvis" || landmark.owner.role === "torso" ? PROVISIONAL_FORM_TORSO_FRAME_ROLE : landmark.owner.role === "neck" || landmark.owner.role === "head" ? PROVISIONAL_FORM_HEAD_NECK_FRAME_ROLE : PROVISIONAL_FORM_SHOULDER_FRAME_ROLE;
      if (!formHasExactFields(landmark.frame, ["owner", "role"]) || !formAddressEquals(landmark.frame.owner, landmark.owner) || landmark.frame.role !== expectedFrameRole) {
        errors.push(where + " frame must reference its same-owner control frame.");
      }
      var frameKey = isObject(landmark.frame.owner) ? JSON.stringify([landmark.frame.owner.namespace, landmark.frame.owner.anchors, landmark.frame.owner.kind, landmark.frame.owner.role, landmark.frame.role]) : "";
      if (!frameMap[frameKey]) { errors.push(where + " frame references an unlisted authored frame."); }
      if (!formFiniteVector(landmark.position, 3) || landmark.position.some(function (component) { return Math.abs(component) > 1.0; })) {
        errors.push(where + " position must be finite and within +/-1.0.");
      }
      if ((landmark.owner.role === "pelvis" || landmark.owner.role === "torso") && (!formFiniteVector(landmark.position, 3) || landmark.position[0] !== 0 || landmark.position[2] !== 0)) {
        errors.push(where + " position must be an axial [0,y,0] point.");
      }
      if ((landmark.owner.role === "neck" || landmark.owner.role === "head") && (!formFiniteVector(landmark.position, 3) || landmark.position[0] !== 0)) {
        errors.push(where + " position must be an axial [0,y,z] point.");
      }
      if (includeV9Controls && landmark.role.indexOf("form_arm_profile_") === 0 && (!formFiniteVector(landmark.position, 3) || landmark.owner.role !== "upper_arm" && landmark.owner.role !== "forearm" || landmark.position[0] !== 0 || landmark.position[2] !== 0)) {
        errors.push(where + " position must be an axial [0,y,0] point.");
      }
      if (includeV10Controls && landmark.role.indexOf("form_leg_profile_") === 0 && (!formFiniteVector(landmark.position, 3) || landmark.owner.role !== "thigh" && landmark.owner.role !== "shin" || landmark.position[0] !== 0 || landmark.position[2] !== 0)) {
        errors.push(where + " position must be an axial [0,y,0] point.");
      }
      if (includeV10Controls && landmark.role.indexOf("form_leg_profile_") === 0 && (!formFiniteVector(landmark.position, 3) || landmark.position[1] < -1.0 || landmark.position[1] > 0.0)) {
        errors.push(where + " position y must be in inclusive [-1.0, 0.0].");
      }
    });
    if (Object.keys(landmarkMap).length !== Object.keys(expectedLandmarkKeys).length || Object.keys(expectedLandmarkKeys).some(function (key) { return !landmarkMap[key]; })) {
      errors.push(contractLabel + " authored landmarks must contain the exact control inventory.");
    }
    if (landmarkOrder.some(function (key, index) { return index > 0 && key < landmarkOrder[index - 1]; })) {
      errors.push("v8 authored landmarks must use stable owner/role order.");
    }

    var dimensions = Array.isArray(payload.authored_dimensions) ? payload.authored_dimensions : [];
    var dimensionMap = {};
    dimensions.forEach(function (dimension, index) {
      var where = "v8 authored dimension " + index;
      if (!formHasExactFields(dimension, ["owner", "role", "value_permille", "provenance"]) || !formHasExactFields(dimension.owner, ["namespace", "anchors", "kind", "role"]) || typeof dimension.role !== "string" || !isObject(dimension.provenance) || !Number.isInteger(dimension.value_permille) || dimension.value_permille <= 0 || dimension.value_permille > 5000) {
        errors.push(where + " is incomplete, unknown, or outside the positive permille bound.");
        return;
      }
      var key = formDimensionKey(dimension.owner, dimension.role);
      if (dimensionMap[key]) { errors.push(where + " duplicates an owner/role key."); }
      dimensionMap[key] = dimension;
      if (dimension.owner.namespace !== namespace || !formControlProvenance(dimension.provenance, source) || !formHasExactFields(dimension.provenance, ["source", "document", "namespace"])) {
        errors.push(where + " has invalid source provenance or namespace.");
      }
    });
    var profile = payload.authored_head_neck_profile;
    if (!formHasExactFields(profile, ["format", "provenance", "sections", "connections"]) || profile.format !== PROVISIONAL_FORM_HEAD_NECK_PROFILE_FORMAT || !formControlProvenance(profile.provenance, source) || !formHasExactFields(profile.provenance, ["source", "document", "namespace"]) || !Array.isArray(profile.sections) || !Array.isArray(profile.connections)) {
      errors.push("v8 authored_head_neck_profile has an unexpected format, provenance, or fields.");
      return { errors: errors, dimensionKeys: dimensionKeys, sourceSections: sourceSections };
    }
    if (profile.connections.length !== PROVISIONAL_FORM_HEAD_NECK_CONNECTIONS.length) {
      errors.push("v8 authored_head_neck_profile must contain exactly seven connections.");
    }
    PROVISIONAL_FORM_HEAD_NECK_CONNECTIONS.forEach(function (expected, index) {
      var connection = profile.connections[index];
      var where = "v8 head/neck profile connection " + index;
      if (!formHasExactFields(connection, ["name", "from_section_index", "to_section_index", "route"])) {
        errors.push(where + " is incomplete or has unknown fields.");
        return;
      }
      if (connection.name !== expected.name || connection.from_section_index !== expected.from || connection.to_section_index !== expected.to || connection.route !== expected.route) {
        errors.push(where + " does not match the exact v8 connection route.");
      }
    });
    if (profile.sections.length !== PROVISIONAL_FORM_HEAD_NECK_SECTIONS.length) {
      errors.push("v8 authored_head_neck_profile must contain exactly eight sections.");
      return { errors: errors, dimensionKeys: dimensionKeys, sourceSections: sourceSections };
    }
    var routeValues = [[], [], []];
    PROVISIONAL_FORM_HEAD_NECK_SECTIONS.forEach(function (expected, index) {
      var section = profile.sections[index];
      var where = "v8 head/neck profile section " + index;
      var sourceSection = { name: expected.name, ownerRole: expected.ownerRole, position: null, radii: {} };
      sourceSections.push(sourceSection);
      if (!formHasExactFields(section, ["name", "frame_index", "landmark_index", "dimension_indices", "provenance", "section_index"]) || !isObject(section.dimension_indices) || !formControlProvenance(section.provenance, source) || !formHasExactFields(section.provenance, ["source", "document", "namespace"])) {
        errors.push(where + " is incomplete or has unknown fields.");
        return;
      }
      if (section.name !== expected.name || section.section_index !== index) {
        errors.push(where + " is not in the required stable order.");
      }
      var owner = formHeadNeckOwner(namespace, expected.ownerRole);
      if (!Number.isInteger(section.frame_index) || section.frame_index < 0 || section.frame_index >= frames.length) {
        errors.push(where + " frame_index must be an in-range integer index.");
      } else if (!formAddressEquals(frames[section.frame_index].owner, owner) || frames[section.frame_index].role !== PROVISIONAL_FORM_HEAD_NECK_FRAME_ROLE) {
        errors.push(where + " frame_index does not resolve to its identity owner head/neck control frame.");
      }
      var sectionKey = expected.name.replace(/-/g, "_");
      var landmarkRole = "form_head_neck_profile_" + sectionKey;
      if (!Number.isInteger(section.landmark_index) || section.landmark_index < 0 || section.landmark_index >= landmarks.length) {
        errors.push(where + " landmark_index must be an in-range integer index.");
      } else {
        var landmark = landmarks[section.landmark_index];
        if (!isObject(landmark) || !formAddressEquals(landmark.owner, owner) || landmark.role !== landmarkRole) {
          errors.push(where + " landmark_index does not resolve to the canonical section landmark.");
        } else if (formFiniteVector(landmark.position, 3)) {
          sourceSection.position = landmark.position.slice();
          if (index <= 1) { routeValues[0].push(landmark.position[1]); }
          if (index >= 2 && index <= 4) { routeValues[1].push(landmark.position[1]); }
          if (index === 3 || index >= 5) { routeValues[2].push(landmark.position[2]); }
        }
      }
      if (!formHasExactFields(section.dimension_indices, ["lateral", "up", "forward"])) {
        errors.push(where + " dimension_indices must contain exactly lateral, up, and forward.");
        return;
      }
      PROVISIONAL_FORM_HEAD_NECK_RADIUS_FACTORS.forEach(function (factor) {
        var dimensionIndex = section.dimension_indices[factor.name];
        var role = "form_head_neck_profile_" + sectionKey + "_" + factor.roleSuffix;
        if (!Number.isInteger(dimensionIndex) || dimensionIndex < 0 || dimensionIndex >= dimensions.length) {
          errors.push(where + " dimension_indices." + factor.name + " must be an in-range integer index.");
          return;
        }
        var indexedDimension = dimensions[dimensionIndex];
        if (!isObject(indexedDimension) || !formAddressEquals(indexedDimension.owner, owner) || indexedDimension.role !== role) {
          errors.push(where + " dimension_indices." + factor.name + " does not resolve to " + role + ".");
          return;
        }
        var key = formDimensionKey(indexedDimension.owner, indexedDimension.role);
        dimensionKeys[key] = true;
        sourceSection.radii[factor.name] = indexedDimension.value_permille;
      });
    });
    ["y", "y", "z"].forEach(function (axis, routeIndex) {
      if (routeValues[routeIndex].some(function (value, index) { return index > 0 && value <= routeValues[routeIndex][index - 1]; })) {
        errors.push("v8 head/neck profile landmarks must have strictly increasing " + axis + ".");
      }
    });
    return { errors: errors, dimensionKeys: dimensionKeys, sourceSections: sourceSections };
  }

  function formV8VariantHeadNeckProfile(profile, profileId, source, sourceSections) {
    var errors = [];
    var prefix = "Variant " + profileId + " head_neck_profile";
    if (!formHasExactFields(profile, ["format", "source", "provenance", "sections", "connections"]) || profile.format !== PROVISIONAL_FORM_HEAD_NECK_PROFILE_FORMAT || profile.source !== "authored_head_neck_profile" || !formControlProvenance(profile.provenance, source) || !formHasExactFields(profile.provenance, ["source", "document", "namespace"]) || !Array.isArray(profile.sections) || !Array.isArray(profile.connections)) {
      return [prefix + " has an unexpected format, source, provenance, or fields."];
    }
    if (profile.connections.length !== PROVISIONAL_FORM_HEAD_NECK_CONNECTIONS.length) {
      errors.push(prefix + " must contain exactly seven connections.");
    }
    PROVISIONAL_FORM_HEAD_NECK_CONNECTIONS.forEach(function (expected, index) {
      var connection = profile.connections[index];
      var where = prefix + " connection " + index;
      if (!formHasExactFields(connection, ["name", "from_section_index", "to_section_index", "route"])) {
        errors.push(where + " is incomplete or has unknown fields.");
      } else if (connection.name !== expected.name || connection.from_section_index !== expected.from || connection.to_section_index !== expected.to || connection.route !== expected.route) {
        errors.push(where + " does not match the exact v8 connection route.");
      }
    });
    if (profile.sections.length !== sourceSections.length) {
      errors.push(prefix + " must contain exactly eight source-indexed sections.");
      return errors;
    }
    profile.sections.forEach(function (section, index) {
      var where = prefix + " section " + index;
      var sourceSection = sourceSections[index];
      if (!formHasExactFields(section, ["source_section_index", "name", "position", "lateral_radius_permille", "up_radius_permille", "forward_radius_permille", "scaling", "provenance"]) || !isObject(sourceSection) || !isObject(section.scaling) || !formControlProvenance(section.provenance, source) || !formHasExactFields(section.provenance, ["source", "document", "namespace"])) {
        errors.push(where + " is incomplete or has unknown fields.");
        return;
      }
      if (!Number.isInteger(section.source_section_index) || section.source_section_index !== index) { errors.push(where + " source_section_index must equal its stable source index."); }
      if (section.name !== sourceSection.name) { errors.push(where + " name does not match its indexed source section."); }
      if (!formFiniteVector(section.position, 3) || !Array.isArray(sourceSection.position) || !formVectorEquals(section.position, sourceSection.position)) { errors.push(where + " position must equal its indexed source landmark."); }
      var factors = formHeadNeckProfileFactors(profileId, sourceSection.ownerRole);
      var expectedScaling = { lateral_factor_permille: factors.lateral, up_factor_permille: factors.up, forward_factor_permille: factors.forward };
      if (!formHasExactFields(section.scaling, Object.keys(expectedScaling))) { errors.push(where + " scaling must contain exactly the three axis factors."); }
      Object.keys(expectedScaling).forEach(function (field) {
        if (!Number.isInteger(section.scaling[field]) || section.scaling[field] <= 0 || section.scaling[field] > 5000 || section.scaling[field] !== expectedScaling[field]) { errors.push(where + " " + field + " does not match the fixed variant factor."); }
      });
      PROVISIONAL_FORM_HEAD_NECK_RADIUS_FACTORS.forEach(function (factor) {
        var field = factor.name + "_radius_permille";
        var expectedRadius = Number.isInteger(sourceSection.radii[factor.name]) ? Math.floor(sourceSection.radii[factor.name] * factors[factor.name] / 1000) : NaN;
        if (!Number.isInteger(section[field]) || section[field] <= 0 || section[field] > 5000 || section[field] !== expectedRadius) { errors.push(where + " " + field + " does not match its indexed source radius and fixed factor."); }
      });
      if (!formControlProvenance(section.provenance, source)) { errors.push(where + " provenance is not exact source-authored provenance."); }
    });
    return errors;
  }

  function formArmProfileFactors(profileId) {
    if (profileId === "broad-soft-v0") { return { lateral: 1150, up: 1000, forward: 1150 }; }
    if (profileId === "lean-readable-v0") { return { lateral: 800, up: 1000, forward: 800 }; }
    if (profileId === "depth-forward-v0") { return { lateral: 1000, up: 1000, forward: 1300 }; }
    return { lateral: 1000, up: 1000, forward: 1000 };
  }

  function formLegProfileFactors(profileId) {
    return formArmProfileFactors(profileId);
  }

  function formV9AuthoredArmProfile(payload) {
    var errors = [];
    var dimensionKeys = {};
    var sourceSides = [];
    var source = payload.source;
    if (!formHasExactFields(source, ["document", "namespace", "resource_profile_id"]) || typeof source.namespace !== "string" || !source.namespace || typeof source.document !== "string" || !source.document || source.resource_profile_id !== "ck.resource.body.r2") {
      return { errors: ["v9 source identity must provide non-empty namespace and document strings for arm controls."], dimensionKeys: dimensionKeys, sourceSides: sourceSides };
    }
    var namespace = source.namespace;
    var frames = Array.isArray(payload.authored_frames) ? payload.authored_frames : [];
    var landmarks = Array.isArray(payload.authored_landmarks) ? payload.authored_landmarks : [];
    var dimensions = Array.isArray(payload.authored_dimensions) ? payload.authored_dimensions : [];
    var profile = payload.authored_arm_profile;
    if (!formHasExactFields(profile, ["format", "provenance", "sides"]) || profile.format !== PROVISIONAL_FORM_ARM_PROFILE_FORMAT || !formControlProvenance(profile.provenance, source) || !formHasExactFields(profile.provenance, ["source", "document", "namespace"]) || !Array.isArray(profile.sides)) {
      errors.push("v9 authored_arm_profile has an unexpected format, provenance, or fields.");
      return { errors: errors, dimensionKeys: dimensionKeys, sourceSides: sourceSides };
    }
    if (profile.sides.length !== PROVISIONAL_FORM_ARM_SIDES.length) {
      errors.push("v9 authored_arm_profile must contain exactly two sides.");
    }
    PROVISIONAL_FORM_ARM_SIDES.forEach(function (expectedSide, sideIndex) {
      var side = profile.sides[sideIndex];
      var sideWhere = "v9 arm profile side " + sideIndex;
      if (!formHasExactFields(side, ["side", "sections"]) || side.side !== expectedSide || !Array.isArray(side.sections)) {
        errors.push(sideWhere + " is not the exact left/right side record.");
        return;
      }
      if (side.sections.length !== PROVISIONAL_FORM_ARM_SECTIONS.length) {
        errors.push(sideWhere + " must contain exactly five sections.");
        return;
      }
      var sourceSections = [];
      PROVISIONAL_FORM_ARM_SECTIONS.forEach(function (expected, sectionIndex) {
        var section = side.sections[sectionIndex];
        var where = sideWhere + " section " + sectionIndex;
        var sectionKey = expected.name.replace(/-/g, "_");
        var owner = formArmOwner(namespace, expectedSide, expected.ownerRole);
        var landmarkRole = "form_arm_profile_" + sectionKey;
        var sourceSection = { name: expected.name, ownerRole: expected.ownerRole, position: null, radii: {} };
        sourceSections.push(sourceSection);
        if (!formHasExactFields(section, ["name", "frame_index", "landmark_index", "dimension_indices", "provenance", "section_index"]) || !isObject(section.dimension_indices) || !formControlProvenance(section.provenance, source) || !formHasExactFields(section.provenance, ["source", "document", "namespace"])) {
          errors.push(where + " is incomplete or has unknown fields.");
          return;
        }
        if (section.name !== expected.name || section.section_index !== sectionIndex) {
          errors.push(where + " is not in the required stable order.");
        }
        if (!Number.isInteger(section.frame_index) || section.frame_index < 0 || section.frame_index >= frames.length) {
          errors.push(where + " frame_index must be an in-range integer index.");
        } else if (!isObject(frames[section.frame_index]) || !formAddressEquals(frames[section.frame_index].owner, owner) || frames[section.frame_index].role !== PROVISIONAL_FORM_ARM_FRAME_ROLE) {
          errors.push(where + " frame_index does not resolve to its identity owner arm control frame.");
        }
        if (!Number.isInteger(section.landmark_index) || section.landmark_index < 0 || section.landmark_index >= landmarks.length) {
          errors.push(where + " landmark_index must be an in-range integer index.");
        } else {
          var landmark = landmarks[section.landmark_index];
          if (!isObject(landmark) || !formAddressEquals(landmark.owner, owner) || landmark.role !== landmarkRole) {
            errors.push(where + " landmark_index does not resolve to the canonical arm profile landmark.");
          } else if (!formFiniteVector(landmark.position, 3) || landmark.position[0] !== 0 || landmark.position[2] !== 0 || landmark.position.some(function (component) { return Math.abs(component) > 1.0; })) {
            errors.push(where + " landmark position must be an axial [0,y,0] point.");
          } else {
            sourceSection.position = landmark.position.slice();
          }
        }
        if (!formHasExactFields(section.dimension_indices, ["lateral", "up", "forward"])) {
          errors.push(where + " dimension_indices must contain exactly lateral, up, and forward.");
          return;
        }
        PROVISIONAL_FORM_ARM_RADIUS_FACTORS.forEach(function (factor, axisIndex) {
          var dimensionIndex = section.dimension_indices[factor.name];
          var role = "form_arm_profile_" + sectionKey + "_" + factor.roleSuffix;
          if (!Number.isInteger(dimensionIndex) || dimensionIndex < 0 || dimensionIndex >= dimensions.length) {
            errors.push(where + " dimension_indices." + factor.name + " must be an in-range integer index.");
            return;
          }
          var dimension = dimensions[dimensionIndex];
          if (!isObject(dimension) || !formAddressEquals(dimension.owner, owner) || dimension.role !== role) {
            errors.push(where + " dimension_indices." + factor.name + " does not resolve to " + role + ".");
            return;
          }
          dimensionKeys[formDimensionKey(dimension.owner, dimension.role)] = true;
          sourceSection.radii[factor.name] = dimension.value_permille;
          if (!formPositivePermille(dimension.value_permille)) {
            errors.push(where + " " + factor.name + " source radius must be a positive bounded permille value.");
            return;
          }
          PROVISIONAL_FORM_VARIANTS.forEach(function (profileId) {
            var scale = formArmProfileFactors(profileId)[factor.name];
            var scaled = Math.floor(dimension.value_permille * scale / 1000);
            if (!formPositivePermille(scaled)) {
              errors.push(where + " " + factor.name + " source radius exceeds the projected positive bound.");
            }
          });
        });
      });
      sourceSides.push({ side: expectedSide, sections: sourceSections });
    });
    return { errors: errors, dimensionKeys: dimensionKeys, sourceSides: sourceSides };
  }

  function formV9VariantArmProfile(profile, profileId, source, sourceSides) {
    var errors = [];
    var prefix = "Variant " + profileId + " arm_profile";
    if (!formHasExactFields(profile, ["format", "source", "provenance", "sides"]) || profile.format !== PROVISIONAL_FORM_ARM_PROFILE_FORMAT || profile.source !== "authored_arm_profile" || !formControlProvenance(profile.provenance, source) || !formHasExactFields(profile.provenance, ["source", "document", "namespace"]) || !Array.isArray(profile.sides)) {
      return [prefix + " has an unexpected format, source, provenance, or fields."];
    }
    if (profile.sides.length !== sourceSides.length) {
      errors.push(prefix + " must contain exactly two source-indexed sides.");
      return errors;
    }
    profile.sides.forEach(function (side, sideIndex) {
      var sideWhere = prefix + " side " + sideIndex;
      var sourceSide = sourceSides[sideIndex];
      if (!formHasExactFields(side, ["side", "sections"]) || !isObject(sourceSide) || side.side !== sourceSide.side || !Array.isArray(side.sections)) {
        errors.push(sideWhere + " does not match its indexed source side.");
        return;
      }
      if (side.sections.length !== sourceSide.sections.length) {
        errors.push(sideWhere + " must contain exactly five source-indexed sections.");
        return;
      }
      var factors = formArmProfileFactors(profileId);
      side.sections.forEach(function (section, sectionIndex) {
        var where = sideWhere + " section " + sectionIndex;
        var sourceSection = sourceSide.sections[sectionIndex];
        if (!formHasExactFields(section, ["source_section_index", "name", "position", "lateral_radius_permille", "up_radius_permille", "forward_radius_permille", "scaling", "provenance"]) || !isObject(sourceSection) || !isObject(section.scaling) || !formControlProvenance(section.provenance, source) || !formHasExactFields(section.provenance, ["source", "document", "namespace"])) {
          errors.push(where + " is incomplete or has unknown fields.");
          return;
        }
        if (!Number.isInteger(section.source_section_index) || section.source_section_index !== sectionIndex) { errors.push(where + " source_section_index must equal its stable source index."); }
        if (section.name !== sourceSection.name) { errors.push(where + " name does not match its indexed source section."); }
        if (!formFiniteVector(section.position, 3) || !Array.isArray(sourceSection.position) || !formVectorEquals(section.position, sourceSection.position)) { errors.push(where + " position must equal its indexed source landmark."); }
        var expectedScaling = { lateral_factor_permille: factors.lateral, up_factor_permille: factors.up, forward_factor_permille: factors.forward };
        if (!formHasExactFields(section.scaling, Object.keys(expectedScaling))) { errors.push(where + " scaling must contain exactly the three axis factors."); }
        Object.keys(expectedScaling).forEach(function (field) {
          if (!formPositivePermille(section.scaling[field]) || section.scaling[field] !== expectedScaling[field]) { errors.push(where + " " + field + " does not match the fixed variant factor."); }
        });
        PROVISIONAL_FORM_ARM_RADIUS_FACTORS.forEach(function (factor) {
          var field = factor.name + "_radius_permille";
          var expectedRadius = Number.isInteger(sourceSection.radii[factor.name]) ? Math.floor(sourceSection.radii[factor.name] * factors[factor.name] / 1000) : NaN;
          if (!formPositivePermille(section[field]) || section[field] !== expectedRadius) { errors.push(where + " " + field + " does not match its indexed source radius and fixed factor."); }
        });
      });
    });
    return errors;
  }

  function formV10AuthoredLegProfile(payload) {
    var errors = [];
    var dimensionKeys = {};
    var sourceSides = [];
    var source = payload.source;
    if (!formHasExactFields(source, ["document", "namespace", "resource_profile_id"]) || typeof source.namespace !== "string" || !source.namespace || typeof source.document !== "string" || !source.document || source.resource_profile_id !== "ck.resource.body.r2") {
      return { errors: ["v10 source identity must provide non-empty namespace and document strings for leg controls."], dimensionKeys: dimensionKeys, sourceSides: sourceSides };
    }
    var namespace = source.namespace;
    var frames = Array.isArray(payload.authored_frames) ? payload.authored_frames : [];
    var landmarks = Array.isArray(payload.authored_landmarks) ? payload.authored_landmarks : [];
    var dimensions = Array.isArray(payload.authored_dimensions) ? payload.authored_dimensions : [];
    if (frames.filter(function (item) { return isObject(item) && item.role === PROVISIONAL_FORM_LEG_FRAME_ROLE; }).length !== 4) {
      errors.push("v10 leg controls must contain exactly four leg profile frames.");
    }
    if (landmarks.filter(function (item) { return isObject(item) && typeof item.role === "string" && item.role.indexOf("form_leg_profile_") === 0; }).length !== 10) {
      errors.push("v10 leg controls must contain exactly ten leg profile landmarks.");
    }
    var expectedDimensionKeys = {};
    PROVISIONAL_FORM_LEG_SIDES.forEach(function (side) {
      PROVISIONAL_FORM_LEG_SECTIONS.forEach(function (section) {
        var owner = formLegOwner(namespace, side, section.ownerRole);
        PROVISIONAL_FORM_LEG_RADIUS_FACTORS.forEach(function (factor) {
          expectedDimensionKeys[formDimensionKey(owner, "form_leg_profile_" + section.name.replace(/-/g, "_") + "_" + factor.roleSuffix)] = true;
        });
      });
    });
    var actualDimensionKeys = {};
    dimensions.forEach(function (dimension) {
      if (isObject(dimension) && isObject(dimension.owner) && typeof dimension.role === "string" && dimension.role.indexOf("form_leg_profile_") === 0) {
        actualDimensionKeys[formDimensionKey(dimension.owner, dimension.role)] = true;
      }
    });
    var expectedDimensionKeyList = Object.keys(expectedDimensionKeys).sort();
    var actualDimensionKeyList = Object.keys(actualDimensionKeys).sort();
    if (expectedDimensionKeyList.length !== 30 || JSON.stringify(expectedDimensionKeyList) !== JSON.stringify(actualDimensionKeyList)) {
      errors.push("v10 authored dimensions must contain exactly thirty leg profile radius dimensions.");
    }
    var profile = payload.authored_leg_profile;
    if (!formHasExactFields(profile, ["format", "provenance", "sides"]) || profile.format !== PROVISIONAL_FORM_LEG_PROFILE_FORMAT || !formControlProvenance(profile.provenance, source) || !formHasExactFields(profile.provenance, ["source", "document", "namespace"]) || !Array.isArray(profile.sides)) {
      errors.push("v10 authored_leg_profile has an unexpected format, provenance, or fields.");
      return { errors: errors, dimensionKeys: dimensionKeys, sourceSides: sourceSides };
    }
    if (profile.sides.length !== PROVISIONAL_FORM_LEG_SIDES.length) {
      errors.push("v10 authored_leg_profile must contain exactly two sides.");
    }
    PROVISIONAL_FORM_LEG_SIDES.forEach(function (expectedSide, sideIndex) {
      var side = profile.sides[sideIndex];
      var sideWhere = "v10 leg profile side " + sideIndex;
      if (!formHasExactFields(side, ["side", "sections"]) || side.side !== expectedSide || !Array.isArray(side.sections)) {
        errors.push(sideWhere + " is not the exact left/right side record.");
        return;
      }
      if (side.sections.length !== PROVISIONAL_FORM_LEG_SECTIONS.length) {
        errors.push(sideWhere + " must contain exactly five sections.");
        return;
      }
      var sourceSections = [];
      var previousOwner = null;
      var previousY = null;
      PROVISIONAL_FORM_LEG_SECTIONS.forEach(function (expected, sectionIndex) {
        var section = side.sections[sectionIndex];
        var where = sideWhere + " section " + sectionIndex;
        var sectionKey = expected.name.replace(/-/g, "_");
        var owner = formLegOwner(namespace, expectedSide, expected.ownerRole);
        var landmarkRole = "form_leg_profile_" + sectionKey;
        var sourceSection = { name: expected.name, ownerRole: expected.ownerRole, position: null, radii: {} };
        sourceSections.push(sourceSection);
        if (!formHasExactFields(section, ["name", "frame_index", "landmark_index", "dimension_indices", "provenance", "section_index"]) || !isObject(section.dimension_indices) || !formControlProvenance(section.provenance, source) || !formHasExactFields(section.provenance, ["source", "document", "namespace"])) {
          errors.push(where + " is incomplete or has unknown fields.");
          return;
        }
        if (section.name !== expected.name || section.section_index !== sectionIndex) {
          errors.push(where + " is not in the required stable order.");
        }
        if (!Number.isInteger(section.frame_index) || section.frame_index < 0 || section.frame_index >= frames.length) {
          errors.push(where + " frame_index must be an in-range integer index.");
        } else if (!isObject(frames[section.frame_index]) || !formAddressEquals(frames[section.frame_index].owner, owner) || frames[section.frame_index].role !== PROVISIONAL_FORM_LEG_FRAME_ROLE) {
          errors.push(where + " frame_index does not resolve to its identity owner leg control frame.");
        }
        if (!Number.isInteger(section.landmark_index) || section.landmark_index < 0 || section.landmark_index >= landmarks.length) {
          errors.push(where + " landmark_index must be an in-range integer index.");
        } else {
          var landmark = landmarks[section.landmark_index];
          if (!isObject(landmark) || !formAddressEquals(landmark.owner, owner) || landmark.role !== landmarkRole) {
            errors.push(where + " landmark_index does not resolve to the canonical leg profile landmark.");
          } else if (!formFiniteVector(landmark.position, 3) || landmark.position[0] !== 0 || landmark.position[2] !== 0 || landmark.position.some(function (component) { return Math.abs(component) > 1.0; })) {
            errors.push(where + " landmark position must be an axial [0,y,0] point.");
          } else {
            sourceSection.position = landmark.position.slice();
            if (previousOwner !== null && formAddressEquals(previousOwner, owner) && previousY !== null && landmark.position[1] >= previousY) {
              errors.push(where + " landmark position must be strictly ordered toward the distal end within each Part frame.");
            }
            previousOwner = owner;
            previousY = landmark.position[1];
          }
        }
        if (!formHasExactFields(section.dimension_indices, ["lateral", "up", "forward"])) {
          errors.push(where + " dimension_indices must contain exactly lateral, up, and forward.");
          return;
        }
        PROVISIONAL_FORM_LEG_RADIUS_FACTORS.forEach(function (factor) {
          var dimensionIndex = section.dimension_indices[factor.name];
          var role = "form_leg_profile_" + sectionKey + "_" + factor.roleSuffix;
          if (!Number.isInteger(dimensionIndex) || dimensionIndex < 0 || dimensionIndex >= dimensions.length) {
            errors.push(where + " dimension_indices." + factor.name + " must be an in-range integer index.");
            return;
          }
          var dimension = dimensions[dimensionIndex];
          if (!isObject(dimension) || !formAddressEquals(dimension.owner, owner) || dimension.role !== role) {
            errors.push(where + " dimension_indices." + factor.name + " does not resolve to " + role + ".");
            return;
          }
          dimensionKeys[formDimensionKey(dimension.owner, dimension.role)] = true;
          sourceSection.radii[factor.name] = dimension.value_permille;
          if (!formPositivePermille(dimension.value_permille)) {
            errors.push(where + " " + factor.name + " source radius must be a positive bounded permille value.");
            return;
          }
          PROVISIONAL_FORM_VARIANTS.forEach(function (profileId) {
            var scaled = Math.floor(dimension.value_permille * formLegProfileFactors(profileId)[factor.name] / 1000);
            if (!formPositivePermille(scaled)) {
              errors.push(where + " " + factor.name + " source radius exceeds the projected positive bound.");
            }
          });
        });
      });
      sourceSides.push({ side: expectedSide, sections: sourceSections });
    });
    return { errors: errors, dimensionKeys: dimensionKeys, sourceSides: sourceSides };
  }

  function formV10VariantLegProfile(profile, profileId, source, sourceSides) {
    var errors = [];
    var prefix = "Variant " + profileId + " leg_profile";
    if (!formHasExactFields(profile, ["format", "source", "provenance", "sides"]) || profile.format !== PROVISIONAL_FORM_LEG_PROFILE_FORMAT || profile.source !== "authored_leg_profile" || !formControlProvenance(profile.provenance, source) || !formHasExactFields(profile.provenance, ["source", "document", "namespace"]) || !Array.isArray(profile.sides)) {
      return [prefix + " has an unexpected format, source, provenance, or fields."];
    }
    if (profile.sides.length !== sourceSides.length) {
      errors.push(prefix + " must contain exactly two source-indexed sides.");
      return errors;
    }
    profile.sides.forEach(function (side, sideIndex) {
      var sideWhere = prefix + " side " + sideIndex;
      var sourceSide = sourceSides[sideIndex];
      if (!formHasExactFields(side, ["side", "sections"]) || !isObject(sourceSide) || side.side !== sourceSide.side || !Array.isArray(side.sections)) {
        errors.push(sideWhere + " does not match its indexed source side.");
        return;
      }
      if (side.sections.length !== sourceSide.sections.length) {
        errors.push(sideWhere + " must contain exactly five source-indexed sections.");
        return;
      }
      var factors = formLegProfileFactors(profileId);
      side.sections.forEach(function (section, sectionIndex) {
        var where = sideWhere + " section " + sectionIndex;
        var sourceSection = sourceSide.sections[sectionIndex];
        if (!formHasExactFields(section, ["source_section_index", "name", "position", "lateral_radius_permille", "up_radius_permille", "forward_radius_permille", "scaling", "provenance"]) || !isObject(sourceSection) || !isObject(section.scaling) || !formControlProvenance(section.provenance, source) || !formHasExactFields(section.provenance, ["source", "document", "namespace"])) {
          errors.push(where + " is incomplete or has unknown fields.");
          return;
        }
        if (!Number.isInteger(section.source_section_index) || section.source_section_index !== sectionIndex) { errors.push(where + " source_section_index must equal its stable source index."); }
        if (section.name !== sourceSection.name) { errors.push(where + " name does not match its indexed source section."); }
        if (!formFiniteVector(section.position, 3) || !Array.isArray(sourceSection.position) || !formVectorEquals(section.position, sourceSection.position)) { errors.push(where + " position must equal its indexed source landmark."); }
        var expectedScaling = { lateral_factor_permille: factors.lateral, up_factor_permille: factors.up, forward_factor_permille: factors.forward };
        if (!formHasExactFields(section.scaling, Object.keys(expectedScaling))) { errors.push(where + " scaling must contain exactly the three axis factors."); }
        Object.keys(expectedScaling).forEach(function (field) {
          if (!formPositivePermille(section.scaling[field]) || section.scaling[field] !== expectedScaling[field]) { errors.push(where + " " + field + " does not match the fixed variant factor."); }
        });
        PROVISIONAL_FORM_LEG_RADIUS_FACTORS.forEach(function (factor) {
          var field = factor.name + "_radius_permille";
          var expectedRadius = Number.isInteger(sourceSection.radii[factor.name]) ? Math.floor(sourceSection.radii[factor.name] * factors[factor.name] / 1000) : NaN;
          if (!formPositivePermille(section[field]) || section[field] !== expectedRadius) { errors.push(where + " " + field + " does not match its indexed source radius and fixed factor."); }
        });
      });
    });
    return errors;
  }

  function formValidation(payload) {
    var errors = [];
    if (!isObject(payload) || PROVISIONAL_FORM_FORMATS.indexOf(payload.format) === -1) {
      return ["The provisional filled-form payload is missing or has an unexpected format."];
    }
    if (payload.operation !== "inspect-provisional-form" || payload.status !== "success" || payload.stage !== "provisional-form") {
      errors.push("The payload is not a successful provisional-form inspection.");
    }
    if (payload.processing_complete !== true || payload.diagnostics_complete !== true || !Array.isArray(payload.diagnostics) || payload.diagnostics.length) {
      errors.push("The payload did not report complete, diagnostic-free processing.");
    }
    if (!isObject(payload.source) || !isObject(payload.reference_scale) || !Array.isArray(payload.variants)) {
      errors.push("Source identity, reference scale, or variants are missing.");
      return errors;
    }
    if (typeof payload.limitations !== "string" || !payload.limitations.trim() || payload.limitations.length > 8192 || payload.limitations.indexOf("Readiness") === -1 || payload.limitations.indexOf("geometry") === -1) {
      errors.push("The limitations must be a non-empty string stating the provisional Readiness and geometry boundary.");
    }
    var referenceScale = payload.reference_scale;
    var referenceScaleParentKey = null;
    var referenceScaleChildKey = null;
    var referenceScaleAxisDelta = null;
    var referenceScaleValid = formHasExactFields(referenceScale, ["parent", "child", "axis_delta", "squared_length", "source"]) &&
      formGeometryAddress(referenceScale.parent) && formGeometryAddress(referenceScale.child) &&
      referenceScale.parent.namespace === payload.source.namespace && referenceScale.child.namespace === payload.source.namespace &&
      !formAddressEquals(referenceScale.parent, referenceScale.child) &&
      formFiniteI64Vector(referenceScale.axis_delta, 3) &&
      typeof referenceScale.squared_length === "number" && isFinite(referenceScale.squared_length) && Number.isInteger(referenceScale.squared_length) && referenceScale.squared_length > 0 &&
      referenceScale.source === "exact-containment-edge";
    if (!referenceScaleValid) {
      errors.push("The reference scale has invalid fields, addresses, or a non-positive squared length.");
    } else {
      referenceScaleParentKey = formAddressKey(referenceScale.parent);
      referenceScaleChildKey = formAddressKey(referenceScale.child);
      referenceScaleAxisDelta = referenceScale.axis_delta;
      var expectedSquaredLength = referenceScaleAxisDelta.reduce(function (sum, component) {
        return sum + component * component;
      }, 0);
      if (!isFinite(expectedSquaredLength) || referenceScale.squared_length !== expectedSquaredLength) {
        errors.push("The reference scale squared length must equal the axis-delta squared length.");
        referenceScaleValid = false;
      }
    }
    var isV5 = payload.format === PROVISIONAL_FORM_V5_FORMAT;
    var isV6 = payload.format === PROVISIONAL_FORM_V6_FORMAT;
    var isV7 = payload.format === PROVISIONAL_FORM_V7_FORMAT;
    var isV8 = payload.format === PROVISIONAL_FORM_V8_FORMAT;
    var isV9 = payload.format === PROVISIONAL_FORM_V9_FORMAT;
    var isV10 = payload.format === PROVISIONAL_FORM_V10_FORMAT;
    var hasShoulderControls = isV6 || isV7 || isV8 || isV9 || isV10;
    var hasAuthoredDimensions = isV5 || hasShoulderControls;
    var closedEnvelopeFields = [
      "format", "operation", "status", "stage", "processing_complete",
      "diagnostics_complete", "diagnostics", "source", "reference_scale",
      "authored_dimensions", "authored_landmarks", "authored_frames",
      "authored_torso_profile", "variants", "limitations"
    ];
    if (isV8 || isV9 || isV10) { closedEnvelopeFields.push("authored_head_neck_profile"); }
    if (isV9 || isV10) { closedEnvelopeFields.push("authored_arm_profile"); }
    if (isV10) { closedEnvelopeFields.push("authored_leg_profile"); }
    if ((isV7 || isV8 || isV9 || isV10) && !formHasExactFields(payload, closedEnvelopeFields)) {
      errors.push((isV10 ? "v10" : isV9 ? "v9" : isV8 ? "v8" : "v7") + " payload must contain exactly the closed envelope fields.");
    }
    if (!hasAuthoredDimensions && Object.prototype.hasOwnProperty.call(payload, "authored_dimensions")) {
      errors.push("v1-v4 formats cannot contain authored dimensions.");
    }
    if (!hasShoulderControls && !isV5 && (Object.prototype.hasOwnProperty.call(payload, "authored_frames") || Object.prototype.hasOwnProperty.call(payload, "authored_landmarks"))) {
      errors.push("v1-v4 formats cannot contain v6 shoulder controls.");
    }
    if (isV5 && (Object.prototype.hasOwnProperty.call(payload, "authored_frames") || Object.prototype.hasOwnProperty.call(payload, "authored_landmarks"))) {
      errors.push("v5 is an authored-dimension-only format and cannot contain v6 shoulder controls.");
    }
    if ((isV7 || isV8 || isV9 || isV10) && !Object.prototype.hasOwnProperty.call(payload, "authored_torso_profile")) {
      errors.push((isV10 ? "v10" : isV9 ? "v9" : isV8 ? "v8" : "v7") + " authored_torso_profile is missing.");
    }
    if (!isV7 && !isV8 && !isV9 && !isV10 && Object.prototype.hasOwnProperty.call(payload, "authored_torso_profile")) {
      errors.push("v1-v6 formats cannot contain authored_torso_profile.");
    }
    if ((isV8 || isV9 || isV10) && !Object.prototype.hasOwnProperty.call(payload, "authored_head_neck_profile")) {
      errors.push((isV10 ? "v10" : isV9 ? "v9" : "v8") + " authored_head_neck_profile is missing.");
    }
    if (!isV8 && !isV9 && !isV10 && Object.prototype.hasOwnProperty.call(payload, "authored_head_neck_profile")) {
      errors.push("v1-v7 formats cannot contain authored_head_neck_profile.");
    }
    if ((isV9 || isV10) && !Object.prototype.hasOwnProperty.call(payload, "authored_arm_profile")) {
      errors.push((isV10 ? "v10" : "v9") + " authored_arm_profile is missing.");
    }
    if (!isV9 && !isV10 && Object.prototype.hasOwnProperty.call(payload, "authored_arm_profile")) {
      errors.push("v1-v8 formats cannot contain authored_arm_profile.");
    }
    if (isV10 && !Object.prototype.hasOwnProperty.call(payload, "authored_leg_profile")) {
      errors.push("v10 authored_leg_profile is missing.");
    }
    if (!isV10 && Object.prototype.hasOwnProperty.call(payload, "authored_leg_profile")) {
      errors.push("v1-v9 formats cannot contain authored_leg_profile.");
    }
    var authoredDimensionKeys = {};
    if (hasAuthoredDimensions) {
      if (!Array.isArray(payload.authored_dimensions) || !payload.authored_dimensions.length) {
        errors.push((isV7 ? "v7" : isV6 ? "v6" : "v5") + " authored dimensions are missing.");
      } else {
        payload.authored_dimensions.forEach(function (dimension, index) {
          if (!isObject(dimension) || !isObject(dimension.owner) || typeof dimension.role !== "string" || !dimension.role || !Number.isInteger(dimension.value_permille) || dimension.value_permille <= 0 || dimension.value_permille > 5000) {
            errors.push((isV7 ? "v7" : isV6 ? "v6" : "v5") + " authored dimension " + index + " is invalid.");
            return;
          }
          authoredDimensionKeys[formDimensionKey(dimension.owner, dimension.role)] = true;
        });
      }
    }
    if (isV6) {
      formV6ShoulderControls(payload).forEach(function (error) { errors.push(error); });
    }
    var torsoProfileResult = { errors: [], dimensionKeys: {}, sourceSections: [] };
    if (isV7) {
      torsoProfileResult = formV7AuthoredTorsoProfile(payload);
      torsoProfileResult.errors.forEach(function (error) { errors.push(error); });
    }
    var headNeckProfileResult = { errors: [], dimensionKeys: {}, sourceSections: [] };
    var armProfileResult = { errors: [], dimensionKeys: {}, sourceSides: [] };
    if (isV8 || isV9 || isV10) {
      torsoProfileResult = formV7AuthoredTorsoProfile(payload, true, isV9 || isV10, isV10);
      torsoProfileResult.errors.forEach(function (error) { errors.push(error); });
      headNeckProfileResult = formV8AuthoredHeadNeckProfile(payload, isV9 || isV10, isV10);
      headNeckProfileResult.errors.forEach(function (error) { errors.push(error); });
      if (isV9 || isV10) {
        armProfileResult = formV9AuthoredArmProfile(payload);
        armProfileResult.errors.forEach(function (error) { errors.push(error); });
      }
    }
    var legProfileResult = { errors: [], dimensionKeys: {}, sourceSides: [] };
    if (isV10) {
      legProfileResult = formV10AuthoredLegProfile(payload);
      legProfileResult.errors.forEach(function (error) { errors.push(error); });
    }
    var consumedDimensionKeys = {};
    if (isV7 || isV8 || isV9 || isV10) {
      Object.keys(torsoProfileResult.dimensionKeys).forEach(function (key) { consumedDimensionKeys[key] = true; });
    }
    if (isV8 || isV9 || isV10) {
      Object.keys(headNeckProfileResult.dimensionKeys).forEach(function (key) { consumedDimensionKeys[key] = true; });
    }
    if (isV9 || isV10) {
      Object.keys(armProfileResult.dimensionKeys).forEach(function (key) { consumedDimensionKeys[key] = true; });
    }
    if (isV10) {
      Object.keys(legProfileResult.dimensionKeys).forEach(function (key) { consumedDimensionKeys[key] = true; });
    }
    var variantDescriptorMaps = [];
    if (payload.variants.length !== 4) { errors.push("Exactly four fixed variants are required."); }
    payload.variants.forEach(function (variant, index) {
      if (!isObject(variant) || variant.id !== PROVISIONAL_FORM_VARIANTS[index] || variant.profile_id !== PROVISIONAL_FORM_VARIANTS[index] || !Array.isArray(variant.descriptors)) {
        errors.push("Variant " + (index + 1) + " does not match the fixed profile contract.");
        return;
      }
      if ((isV7 || isV8 || isV9 || isV10) && !formHasExactFields(variant, ["id", "profile_id", "provenance", "descriptors", "torso_profile"].concat(isV8 || isV9 || isV10 ? ["head_neck_profile"] : []).concat(isV9 || isV10 ? ["arm_profile"] : []).concat(isV10 ? ["leg_profile"] : []))) {
        errors.push("Variant " + variant.id + " must contain exactly the closed " + (isV10 ? "v10" : isV9 ? "v9" : isV8 ? "v8" : "v7") + " variant fields.");
      }
      if (!isV7 && !isV8 && !isV9 && !isV10 && Object.prototype.hasOwnProperty.call(variant, "torso_profile")) {
        errors.push("v1-v6 variants cannot contain torso_profile.");
      }
      if (!isV8 && !isV9 && !isV10 && Object.prototype.hasOwnProperty.call(variant, "head_neck_profile")) {
        errors.push("v1-v7 variants cannot contain head_neck_profile.");
      }
      if (!isV9 && !isV10 && Object.prototype.hasOwnProperty.call(variant, "arm_profile")) {
        errors.push("v1-v8 variants cannot contain arm_profile.");
      }
      if (!variant.descriptors.length || variant.descriptors.length > 64) {
        errors.push("Variant " + variant.id + " has an invalid descriptor count.");
      }
      if (hasAuthoredDimensions && (!isObject(variant.provenance) || variant.provenance.shape_basis !== "source-authored-dimensions-plus-fixed-display-factor")) {
        errors.push("Variant " + variant.id + " has invalid " + (isV7 ? "v7" : isV6 ? "v6" : "v5") + " shape-basis provenance.");
      }
      if (isV7 || isV8 || isV9 || isV10) {
        formV7VariantTorsoProfile(variant.torso_profile, variant.id, payload.source, torsoProfileResult.sourceSections).forEach(function (error) {
          errors.push(error);
        });
      }
      if (isV8 || isV9 || isV10) {
        formV8VariantHeadNeckProfile(variant.head_neck_profile, variant.id, payload.source, headNeckProfileResult.sourceSections).forEach(function (error) {
          errors.push(error);
        });
      }
      if (isV9 || isV10) {
        formV9VariantArmProfile(variant.arm_profile, variant.id, payload.source, armProfileResult.sourceSides).forEach(function (error) {
          errors.push(error);
        });
      }
      if (isV10) {
        formV10VariantLegProfile(variant.leg_profile, variant.id, payload.source, legProfileResult.sourceSides).forEach(function (error) {
          errors.push(error);
        });
      }
      var v6UpperArmKeys = {};
      var descriptorMap = {};
      variant.descriptors.forEach(function (descriptor, descriptorIndex) {
        if (!isObject(descriptor) || !isObject(descriptor.address) || !isObject(descriptor.shape) || !Array.isArray(descriptor.reference_point)) {
          errors.push("Variant " + variant.id + " descriptor " + descriptorIndex + " is incomplete.");
          return;
        }
        var descriptorWhere = "Variant " + variant.id + " descriptor " + descriptorIndex;
        var addressValid = formGeometryAddress(descriptor.address);
        if (!addressValid) {
          errors.push(descriptorWhere + " has an invalid address.");
        }
        var descriptorKey = formAddressKey(descriptor.address);
        if (addressValid && descriptorMap[descriptorKey]) {
          errors.push(descriptorWhere + " duplicates an address.");
        }
        var referencePointValid = formFiniteI64Vector(descriptor.reference_point, 3);
        if (!referencePointValid) {
          errors.push(descriptorWhere + " reference_point must be a finite signed-i64 vector.");
        }
        var parentValid = descriptor.parent === null || formGeometryAddress(descriptor.parent);
        if (!parentValid) {
          errors.push(descriptorWhere + " parent must be null or a valid address.");
        }
        var parentKey = descriptor.parent === null || !parentValid ? null : formAddressKey(descriptor.parent);
        if (["ellipsoid", "capsule", "tapered-segment"].indexOf(descriptor.shape.name) === -1) {
          errors.push("Variant " + variant.id + " contains an unknown shape.");
        }
        var expectedShape = addressValid ? formDescriptorShape(payload.format, descriptor.address.role) : null;
        if (!expectedShape) {
          errors.push(descriptorWhere + " has an unsupported descriptor role.");
        } else if (descriptor.shape.name !== expectedShape) {
          errors.push(descriptorWhere + " shape must be " + expectedShape + " for its role.");
        }
        var shape = descriptor.shape;
        if (shape.name === "ellipsoid") {
          if (!formHasExactFields(shape, ["name", "center", "axis_extents_permille"])) {
            errors.push(descriptorWhere + " ellipsoid has unknown or missing fields.");
          }
          var centerValid = formFiniteI64Vector(shape.center, 3);
          if (!centerValid) {
            errors.push(descriptorWhere + " ellipsoid center must be a finite signed-i64 vector.");
          } else if (referencePointValid && !formVectorEquals(shape.center, descriptor.reference_point)) {
            errors.push(descriptorWhere + " ellipsoid center must equal reference_point.");
          }
          if (!Array.isArray(shape.axis_extents_permille) || shape.axis_extents_permille.length !== 3 || shape.axis_extents_permille.some(function (extent) { return !formPositivePermille(extent); })) {
            errors.push(descriptorWhere + " ellipsoid extents must be three positive permille values.");
          }
        } else if (shape.name === "capsule") {
          if (!formHasExactFields(shape, ["name", "from", "to", "radius_permille"])) {
            errors.push(descriptorWhere + " capsule has unknown or missing fields.");
          }
          var capsuleFromValid = formFiniteI64Vector(shape.from, 3);
          var capsuleToValid = formFiniteI64Vector(shape.to, 3);
          if (!capsuleFromValid || !capsuleToValid) {
            errors.push(descriptorWhere + " capsule endpoints must be finite signed-i64 vectors.");
          } else if (formVectorEquals(shape.from, shape.to)) {
            errors.push(descriptorWhere + " capsule endpoints must differ.");
          }
          if (!formPositivePermille(shape.radius_permille)) {
            errors.push(descriptorWhere + " capsule radius must be a positive permille value.");
          }
          if (descriptor.parent === null) {
            errors.push(descriptorWhere + " capsule must have a parent.");
          }
          if (payload.format === PROVISIONAL_FORM_FORMATS[0] && referencePointValid && capsuleToValid && !formVectorEquals(shape.to, descriptor.reference_point)) {
            errors.push(descriptorWhere + " legacy capsule end must equal reference_point.");
          }
        } else if (shape.name === "tapered-segment") {
          if (!formHasExactFields(shape, ["name", "from", "to", "start_radius_permille", "end_radius_permille"])) {
            errors.push(descriptorWhere + " tapered segment has unknown or missing fields.");
          }
          var taperedFromValid = formFiniteI64Vector(shape.from, 3);
          var taperedToValid = formFiniteI64Vector(shape.to, 3);
          if (!taperedFromValid || !taperedToValid) {
            errors.push(descriptorWhere + " tapered endpoints must be finite signed-i64 vectors.");
          } else if (formVectorEquals(shape.from, shape.to)) {
            errors.push(descriptorWhere + " tapered endpoints must differ.");
          }
          if (!formPositivePermille(shape.start_radius_permille) || !formPositivePermille(shape.end_radius_permille)) {
            errors.push(descriptorWhere + " tapered radii must be positive permille values.");
          }
          if (descriptor.parent === null) {
            errors.push(descriptorWhere + " tapered segment must have a parent.");
          }
          if (referencePointValid && taperedToValid && !formVectorEquals(shape.to, descriptor.reference_point)) {
            errors.push(descriptorWhere + " tapered end must equal reference_point.");
          }
        }
        if (hasShoulderControls && descriptor.address.role === "upper_arm") {
          var upperArmSide = Array.isArray(descriptor.address.anchors) && descriptor.address.anchors.length === 1 ? descriptor.address.anchors[0] : null;
          if (["left", "right"].indexOf(upperArmSide) === -1 || descriptor.address.namespace !== payload.source.namespace || descriptor.address.kind !== "part") {
            errors.push("Variant " + variant.id + " must contain only left/right upper_arm descriptors for shoulder controls.");
          } else {
            if (v6UpperArmKeys[upperArmSide]) {
              errors.push("Variant " + variant.id + " contains a duplicate " + upperArmSide + " upper_arm descriptor.");
            }
            v6UpperArmKeys[upperArmSide] = true;
          }
          if (descriptor.shape.name !== "capsule") {
            errors.push("Variant " + variant.id + " upper_arm must remain a capsule display shape.");
          }
        }
        if (hasAuthoredDimensions) {
          var expectedRoles = descriptor.shape.name === "ellipsoid" ? ["form_extent_x", "form_extent_y", "form_extent_z"] : descriptor.shape.name === "capsule" ? (hasShoulderControls && descriptor.address.role === "upper_arm" ? ["form_radius", "form_shoulder_depth_radius"] : ["form_radius"]) : ["form_start_radius", "form_end_radius"];
          if (!Array.isArray(descriptor.dimension_roles) || JSON.stringify(descriptor.dimension_roles) !== JSON.stringify(expectedRoles)) {
            errors.push("Variant " + variant.id + " descriptor " + descriptorIndex + " has invalid " + (isV7 ? "v7" : isV6 ? "v6" : "v5") + " dimension-role references.");
          } else {
            descriptor.dimension_roles.forEach(function (role) {
              var key = formDimensionKey(descriptor.address, role);
              consumedDimensionKeys[key] = true;
              if (!authoredDimensionKeys[key]) {
                errors.push("Variant " + variant.id + " descriptor " + descriptorIndex + " references an unlisted " + (isV7 ? "v7" : isV6 ? "v6" : "v5") + " authored dimension.");
              }
            });
          }
        }
        if (addressValid && !descriptorMap[descriptorKey]) {
          descriptorMap[descriptorKey] = {
            descriptor: descriptor,
            parentKey: parentKey,
            referencePoint: descriptor.reference_point,
            referencePointValid: referencePointValid
          };
        }
      });
      Object.keys(descriptorMap).forEach(function (descriptorKey) {
        var record = descriptorMap[descriptorKey];
        var descriptor = record.descriptor;
        var shape = descriptor.shape;
        if (record.parentKey !== null && !descriptorMap[record.parentKey]) {
          errors.push("Variant " + variant.id + " descriptor parent is missing.");
          return;
        }
        if (!record.referencePointValid || !record.parentKey || !descriptorMap[record.parentKey]) {
          return;
        }
        var parentPoint = descriptorMap[record.parentKey].referencePoint;
        if (shape.name === "tapered-segment" && formFiniteI64Vector(shape.from, 3) && !formVectorEquals(shape.from, parentPoint)) {
          errors.push("Variant " + variant.id + " tapered segment start must equal its parent point.");
        }
        if (shape.name === "capsule") {
          if (payload.format === PROVISIONAL_FORM_FORMATS[0]) {
            if (formFiniteI64Vector(shape.from, 3) && !formVectorEquals(shape.from, parentPoint)) {
              errors.push("Variant " + variant.id + " legacy capsule start must equal its parent point.");
            }
          } else {
            if (formFiniteI64Vector(shape.from, 3) && !formVectorEquals(shape.from, record.referencePoint)) {
              errors.push("Variant " + variant.id + " capsule start must equal its reference point.");
            }
            var expectedChildRole = formCapsuleChildRole(payload.format, descriptor.address.role);
            var directChildren = Object.keys(descriptorMap).filter(function (childKey) {
              var child = descriptorMap[childKey];
              return child.parentKey === descriptorKey && child.descriptor.address.role === expectedChildRole;
            });
            if (directChildren.length !== 1) {
              errors.push("Variant " + variant.id + " capsule must have exactly one direct " + expectedChildRole + " child.");
            } else if (formFiniteI64Vector(shape.to, 3) && !descriptorMap[directChildren[0]].referencePointValid) {
              errors.push("Variant " + variant.id + " capsule child point is invalid.");
            } else if (formFiniteI64Vector(shape.to, 3) && !formVectorEquals(shape.to, descriptorMap[directChildren[0]].referencePoint)) {
              errors.push("Variant " + variant.id + " capsule end must equal its direct child point.");
            }
          }
        }
      });
      variantDescriptorMaps.push(descriptorMap);
      if (hasShoulderControls && (Object.keys(v6UpperArmKeys).length !== 2 || !v6UpperArmKeys.left || !v6UpperArmKeys.right)) {
        errors.push("Every shoulder-control variant must contain exactly one left and one right upper_arm descriptor.");
      }
    });
    if (hasAuthoredDimensions && (Object.keys(authoredDimensionKeys).length !== Object.keys(consumedDimensionKeys).length || Object.keys(authoredDimensionKeys).some(function (key) { return !consumedDimensionKeys[key]; }))) {
      errors.push((isV8 ? "v8" : isV7 ? "v7" : isV6 ? "v6" : "v5") + " authored dimensions must equal the complete descriptor- and profile-consumed control set.");
    }
    if (referenceScaleValid && variantDescriptorMaps.length && (!variantDescriptorMaps[0][referenceScaleParentKey] || !variantDescriptorMaps[0][referenceScaleChildKey])) {
      errors.push("The reference scale must name descriptor addresses in the source namespace.");
    } else if (referenceScaleValid && variantDescriptorMaps.length && variantDescriptorMaps[0][referenceScaleParentKey] && variantDescriptorMaps[0][referenceScaleChildKey]) {
      var scaleCandidates = [];
      var firstDescriptorMap = variantDescriptorMaps[0];
      Object.keys(firstDescriptorMap).forEach(function (childKey) {
        var child = firstDescriptorMap[childKey];
        if (!child.parentKey || !firstDescriptorMap[child.parentKey] || !child.referencePointValid || !firstDescriptorMap[child.parentKey].referencePointValid) {
          return;
        }
        var delta = [0, 1, 2].map(function (axis) {
          return child.referencePoint[axis] - firstDescriptorMap[child.parentKey].referencePoint[axis];
        });
        var squared = delta.reduce(function (sum, component) { return sum + component * component; }, 0);
        if (squared) {
          scaleCandidates.push({ squared: squared, childKey: childKey, childAddress: child.descriptor.address, parentKey: child.parentKey, delta: delta });
        }
      });
      scaleCandidates.sort(function (left, right) {
        if (left.squared !== right.squared) { return left.squared - right.squared; }
        return formAddressCompare(left.childAddress, right.childAddress);
      });
      var selectedScale = scaleCandidates[0];
      if (!selectedScale || selectedScale.squared !== referenceScale.squared_length || selectedScale.childKey !== referenceScaleChildKey || selectedScale.parentKey !== referenceScaleParentKey || !formVectorEquals(selectedScale.delta, referenceScaleAxisDelta)) {
        errors.push("The reference scale must match the selected nonzero descriptor edge.");
      }
    }
    return errors;
  }

  function formCoordinate(value) {
    return typeof value === "number" && isFinite(value) ? value : 0;
  }

  function formShapeRadius(payload, permille) {
    var referenceLength = Math.sqrt(payload.reference_scale.squared_length);
    return referenceLength * Number(permille) / 1000;
  }

  function formShapePoints(descriptor) {
    var shape = descriptor.shape;
    if (shape.name === "ellipsoid") { return [shape.center]; }
    return [shape.from, shape.to];
  }

  function formShapeExtent(payload, descriptor, axis) {
    var shape = descriptor.shape;
    if (shape.name === "ellipsoid") {
      return formShapeRadius(payload, shape.axis_extents_permille[axis]);
    }
    return formShapeRadius(payload, Math.max(shape.radius_permille || 0, shape.start_radius_permille || 0, shape.end_radius_permille || 0));
  }

  function formBounds(payload) {
    var minimum = Infinity;
    var maximum = -Infinity;
    payload.variants.forEach(function (variant) {
      variant.descriptors.forEach(function (descriptor) {
        var points = formShapePoints(descriptor);
        for (var axis = 0; axis < 3; axis += 1) {
          points.forEach(function (point) {
            var value = formCoordinate(point[axis]);
            var extent = formShapeExtent(payload, descriptor, axis);
            minimum = Math.min(minimum, value - extent);
            maximum = Math.max(maximum, value + extent);
          });
        }
      });
    });
    if (!isFinite(minimum) || !isFinite(maximum)) { minimum = -1; maximum = 1; }
    var range = Math.max(maximum - minimum, 1);
    var padding = Math.max(range * 0.06, 0.05);
    return { min: minimum - padding, max: maximum + padding };
  }

  function formTransform(bounds) {
    var plot = { left: 34, top: 22, width: 352, height: 218 };
    var range = Math.max(bounds.max - bounds.min, 1e-9);
    var pixelsPerUnit = Math.min(plot.width / range, plot.height / range);
    return {
      plot: plot,
      x: function (value) { return plot.left + (formCoordinate(value) - bounds.min) * pixelsPerUnit; },
      y: function (value) { return plot.top + plot.height - (formCoordinate(value) - bounds.min) * pixelsPerUnit; },
      radius: function (value) { return Math.max(0, Number(value) * pixelsPerUnit); }
    };
  }

  function formProjectedPoint(point, view, transform) {
    return { x: transform.x(point[view.horizontal]), y: transform.y(point[view.vertical]) };
  }

  function formDepth(descriptor, view) {
    var points = formShapePoints(descriptor);
    return points.reduce(function (sum, point) { return sum + formCoordinate(point[view.depth]); }, 0) / points.length;
  }

  function formDrawLabel(svg, descriptor, view, transform) {
    var point = descriptor.shape.name === "ellipsoid" ? descriptor.shape.center : descriptor.shape.to;
    var projected = formProjectedPoint(point, view, transform);
    svg.appendChild(svgNode("text", { x: projected.x + 4, y: projected.y - 4, "class": "form-part-label" }));
    var labels = svg.lastChild;
    var qualifier = formDescriptorQualifier(descriptor);
    labels.textContent = String(descriptor.address.role || "part") + (qualifier ? " · " + qualifier : "");
  }

  function formDescriptorLabel(descriptor) {
    var qualifier = formDescriptorQualifier(descriptor);
    return String(descriptor.address.role || "part") + (qualifier ? " · " + qualifier : "");
  }

  function formDrawPrimitive(svg, payload, descriptor, view, transform, options, variant) {
    var shape = descriptor.shape;
    var color = formRoleColor(descriptor);
    var outline = "#071019";
    var label = formDescriptorLabel(descriptor);
    var activatesInspector = options && typeof options.onActivate === "function";
    var part = svgNode("g", {
      "class": "form-part" + (options && options.showLabels ? " form-part-labels-visible" : ""),
      "data-address-key": formAddressKey(descriptor.address),
      tabindex: "0",
      focusable: "true",
      role: activatesInspector ? "button" : "img",
      "aria-label": activatesInspector ? "Inspect " + variant.id + " · " + label : label
    });
    var title = svgNode("title");
    title.textContent = label;
    part.appendChild(title);
    svg.appendChild(part);
    if (activatesInspector) {
      var activate = function (event) {
        if (event.type === "keydown" && event.key !== "Enter" && event.key !== " ") { return; }
        if (event.type === "keydown") { event.preventDefault(); }
        options.onActivate(variant, descriptor);
      };
      part.addEventListener("click", activate);
      part.addEventListener("keydown", activate);
    }
    if (shape.name === "ellipsoid") {
      var center = formProjectedPoint(shape.center, view, transform);
      var rx = transform.radius(formShapeRadius(payload, shape.axis_extents_permille[view.horizontal]));
      var ry = transform.radius(formShapeRadius(payload, shape.axis_extents_permille[view.vertical]));
      part.appendChild(svgNode("ellipse", { cx: center.x, cy: center.y, rx: rx, ry: ry, fill: color, "fill-opacity": "0.76", stroke: outline, "stroke-width": 1.6, "class": "form-primitive" }));
      formDrawLabel(part, descriptor, view, transform);
      return;
    }
    var from = formProjectedPoint(shape.from, view, transform);
    var to = formProjectedPoint(shape.to, view, transform);
    var radiusValue = shape.name === "capsule" ? shape.radius_permille : Math.max(shape.start_radius_permille, shape.end_radius_permille);
    var radius = transform.radius(formShapeRadius(payload, radiusValue));
    var dx = to.x - from.x;
    var dy = to.y - from.y;
    var length = Math.sqrt(dx * dx + dy * dy);
    if (shape.name === "capsule" || length < 0.001) {
      part.appendChild(svgNode("line", { x1: from.x, y1: from.y, x2: to.x, y2: to.y, stroke: outline, "stroke-width": radius * 2 + 3, "stroke-linecap": "round", fill: "none", "class": "form-primitive" }));
      part.appendChild(svgNode("line", { x1: from.x, y1: from.y, x2: to.x, y2: to.y, stroke: color, "stroke-width": radius * 2, "stroke-linecap": "round", fill: "none", "class": "form-primitive" }));
    } else {
      var nx = -dy / length;
      var ny = dx / length;
      var startRadius = transform.radius(formShapeRadius(payload, shape.start_radius_permille));
      var endRadius = transform.radius(formShapeRadius(payload, shape.end_radius_permille));
      var points = [[from.x + nx * startRadius, from.y + ny * startRadius], [to.x + nx * endRadius, to.y + ny * endRadius], [to.x - nx * endRadius, to.y - ny * endRadius], [from.x - nx * startRadius, from.y - ny * startRadius]];
      part.appendChild(svgNode("polygon", { points: points.map(function (point) { return point.join(","); }).join(" "), fill: color, "fill-opacity": "0.78", stroke: outline, "stroke-width": 1.6, "class": "form-primitive" }));
      part.appendChild(svgNode("circle", { cx: from.x, cy: from.y, r: startRadius, fill: color, "fill-opacity": "0.78", stroke: outline, "stroke-width": 1.6, "class": "form-primitive" }));
      part.appendChild(svgNode("circle", { cx: to.x, cy: to.y, r: endRadius, fill: color, "fill-opacity": "0.78", stroke: outline, "stroke-width": 1.6, "class": "form-primitive" }));
    }
    formDrawLabel(part, descriptor, view, transform);
  }

  function formPanel(payload, variant, view, bounds, options) {
    options = options || {};
    var panel = node("article", null, "form-panel" + (options.large ? " form-panel-large" : ""));
    panel.appendChild(node("h4", view.title));
    panel.appendChild(node("p", view.description, "form-panel-description"));
    var svg = document.createElementNS(SVG_NAMESPACE, "svg");
    svg.setAttribute("viewBox", "0 0 420 270");
    svg.setAttribute("class", "form-svg" + (options.large ? " form-svg-large" : ""));
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", variant.id + " " + view.title);
    svg.appendChild(svgNode("rect", { x: 0, y: 0, width: 420, height: 270, "class": "form-background" }));
    var transform = formTransform(bounds);
    svg.appendChild(svgNode("rect", { x: transform.plot.left, y: transform.plot.top, width: transform.plot.width, height: transform.plot.height, "class": "form-plot" }));
    svg.appendChild(svgNode("line", { x1: transform.plot.left, y1: transform.y(0), x2: transform.plot.left + transform.plot.width, y2: transform.y(0), "class": "form-axis" }));
    svg.appendChild(svgNode("line", { x1: transform.x(0), y1: transform.plot.top, x2: transform.x(0), y2: transform.plot.top + transform.plot.height, "class": "form-axis" }));
    svg.appendChild(svgNode("text", { x: 394, y: 258, "class": "form-axis-label" }));
    svg.lastChild.textContent = view.horizontalLabel;
    svg.appendChild(svgNode("text", { x: 10, y: 28, "class": "form-axis-label" }));
    svg.lastChild.textContent = view.verticalLabel;
    var descriptors = variant.descriptors.slice().sort(function (left, right) {
      var depth = formDepth(left, view) - formDepth(right, view);
      return depth || (formAddressKey(left.address) < formAddressKey(right.address) ? -1 : 1);
    });
    descriptors.forEach(function (descriptor) { formDrawPrimitive(svg, payload, descriptor, view, transform, options, variant); });
    panel.appendChild(svg);
    return panel;
  }

  function formSetInspectHighlight(dialog, addressKey) {
    dialog.classList.toggle("form-has-highlight", Boolean(addressKey));
    Array.prototype.forEach.call(dialog.querySelectorAll(".form-part"), function (part) {
      part.classList.toggle("form-part-highlighted", Boolean(addressKey) && part.getAttribute("data-address-key") === addressKey);
    });
    Array.prototype.forEach.call(dialog.querySelectorAll(".form-inspect-legend-row"), function (row) {
      var selected = Boolean(addressKey) && row.getAttribute("data-address-key") === addressKey;
      row.classList.toggle("form-inspect-legend-row-active", selected);
    });
  }

  function formInspectLegend(variant, dialog) {
    var section = node("section", null, "form-inspect-legend");
    section.appendChild(node("h3", "Parts in this variant"));
    var list = node("ul");
    var hoveredAddressKey = null;
    var focusedAddressKey = null;
    function updateHighlight() {
      formSetInspectHighlight(dialog, hoveredAddressKey || focusedAddressKey);
    }
    variant.descriptors.slice().sort(function (left, right) {
      return formAddressKey(left.address).localeCompare(formAddressKey(right.address));
    }).forEach(function (descriptor) {
      var item = node("li");
      var label = formDescriptorLabel(descriptor);
      var addressKey = formAddressKey(descriptor.address);
      var row = node("button", null, "form-inspect-legend-row");
      row.type = "button";
      row.setAttribute("data-address-key", addressKey);
      row.setAttribute("aria-label", "Highlight " + label + " across all three projections");
      row.appendChild(node("strong", label));
      row.appendChild(node("span", " · " + descriptor.shape.name));
      row.addEventListener("mouseenter", function () {
        hoveredAddressKey = addressKey;
        updateHighlight();
      });
      row.addEventListener("mouseleave", function () {
        hoveredAddressKey = null;
        updateHighlight();
      });
      row.addEventListener("focus", function () {
        focusedAddressKey = addressKey;
        updateHighlight();
      });
      row.addEventListener("blur", function () {
        focusedAddressKey = null;
        updateHighlight();
      });
      item.appendChild(row);
      list.appendChild(item);
    });
    section.appendChild(list);
    return section;
  }

  var formInspectScrollLock = null;

  function lockFormInspectScroll() {
    if (formInspectScrollLock) {
      formInspectScrollLock.count += 1;
    } else {
      var root = document.documentElement;
      var body = document.body;
      var scrollX = window.scrollX;
      var scrollY = window.scrollY;
      var scrollbarWidth = Math.max(0, window.innerWidth - root.clientWidth);
      var bodyPaddingRight = parseFloat(window.getComputedStyle(body).paddingRight) || 0;
      formInspectScrollLock = {
        count: 1,
        scrollX: scrollX,
        scrollY: scrollY,
        root: root,
        body: body,
        rootOverflow: root.style.overflow,
        bodyPosition: body.style.position,
        bodyTop: body.style.top,
        bodyLeft: body.style.left,
        bodyRight: body.style.right,
        bodyWidth: body.style.width,
        bodyOverflow: body.style.overflow,
        bodyPaddingRight: body.style.paddingRight
      };
      root.style.overflow = "hidden";
      body.style.position = "fixed";
      body.style.top = -scrollY + "px";
      body.style.left = -scrollX + "px";
      body.style.right = "0";
      body.style.width = "100%";
      body.style.overflow = "hidden";
      if (scrollbarWidth) {
        body.style.paddingRight = bodyPaddingRight + scrollbarWidth + "px";
      }
    }
    var released = false;
    return function () {
      if (released || !formInspectScrollLock) { return; }
      released = true;
      formInspectScrollLock.count -= 1;
      if (formInspectScrollLock.count) { return; }
      var lock = formInspectScrollLock;
      formInspectScrollLock = null;
      lock.root.style.overflow = lock.rootOverflow;
      lock.body.style.position = lock.bodyPosition;
      lock.body.style.top = lock.bodyTop;
      lock.body.style.left = lock.bodyLeft;
      lock.body.style.right = lock.bodyRight;
      lock.body.style.width = lock.bodyWidth;
      lock.body.style.overflow = lock.bodyOverflow;
      lock.body.style.paddingRight = lock.bodyPaddingRight;
      window.scrollTo(lock.scrollX, lock.scrollY);
    };
  }

  function openFormInspector(payload, variant, trigger) {
    var dialog = node("dialog", null, "form-inspect-dialog");
    var headingId = "form-inspect-heading-" + Math.random().toString(36).slice(2);
    dialog.setAttribute("aria-labelledby", headingId);
    var header = node("header", null, "form-inspect-header");
    var heading = node("h2", "Expanded inspection · " + variant.id);
    heading.id = headingId;
    header.appendChild(heading);
    var close = node("button", "Close", "close-dialog");
    close.type = "button";
    close.addEventListener("click", function () { dialog.close(); });
    header.appendChild(close);
    dialog.appendChild(header);
    dialog.appendChild(node("p", "Use the parts legend below, or hover and keyboard-focus one shape to reveal only its label. Escape or Close returns to the comparison gallery.", "form-inspect-description"));
    var grid = node("div", null, "form-inspect-grid");
    var bounds = formBounds(payload);
    PROVISIONAL_FORM_VIEWS.forEach(function (view) {
      grid.appendChild(formPanel(payload, variant, view, bounds, { large: true }));
    });
    dialog.appendChild(grid);
    dialog.appendChild(formInspectLegend(variant, dialog));
    var releaseScrollLock = lockFormInspectScroll();
    dialog.addEventListener("close", function () {
      dialog.remove();
      if (trigger && typeof trigger.focus === "function" && document.contains(trigger)) {
        try { trigger.focus({ preventScroll: true }); } catch (error) { trigger.focus(); }
      }
      releaseScrollLock();
    });
    document.body.appendChild(dialog);
    try {
      dialog.showModal();
    } catch (error) {
      dialog.remove();
      releaseScrollLock();
      throw error;
    }
    close.focus();
  }

  function provisionalFormPreviewSection(payload) {
    var section = node("section", null, "provisional-form-preview");
    section.appendChild(node("h2", "Filled primitive comparison"));
    section.appendChild(node("p", "All panels use one shared scale and bounds across every variant and projection. Overlapping filled ellipsoids, capsules, and tapered segments are drawn in deterministic depth order; this is not a continuous surface.", "form-explanation"));
    var bounds = formBounds(payload);
    var grid = node("div", null, "form-variant-grid");
    payload.variants.forEach(function (variant) {
      var card = node("article", null, "form-variant-card");
      var heading = node("h3", variant.id);
      heading.appendChild(node("span", variant.profile_id, "form-profile-pill"));
      card.appendChild(heading);
      var panels = node("div", null, "form-panel-grid");
      PROVISIONAL_FORM_VIEWS.forEach(function (view) {
        panels.appendChild(formPanel(payload, variant, view, bounds, {
          onActivate: function (selectedVariant, descriptor) {
            openFormInspector(payload, selectedVariant, document.activeElement);
          }
        }));
      });
      card.appendChild(panels);
      grid.appendChild(card);
    });
    section.appendChild(grid);
    var legend = node("p", null, "form-legend");
    legend.textContent = "Role colors: core/torso teal · head/neck blue · left violet · right orange · tail pink · hands/feet gold. Hover or focus a part to reveal its label; click or press Enter/Space for an expanded inspection.";
    section.appendChild(legend);
    return section;
  }

  function renderProvisionalForm(rawPayload, review) {
    clear(app);
    var payload = rawPayload;
    var title = review && review.title ? String(review.title) : "Provisional filled form";
    document.title = title;
    var back = node("a", "← All reviews", "back-link");
    back.href = "/";
    app.appendChild(back);
    app.appendChild(node("h1", title));
    app.appendChild(node("code", "read-only", "stable-id"));
    if (review && review.description) { app.appendChild(node("p", review.description, "lede")); }
    var errors = formValidation(payload);
    if (errors.length) {
      var invalid = node("section", null, "form-invalid");
      invalid.appendChild(node("h2", "Filled form unavailable"));
      errors.slice(0, 6).forEach(function (error) { invalid.appendChild(node("p", error)); });
      app.appendChild(invalid);
      app.appendChild(valueDetails("Raw provisional-form JSON", payload));
      return;
    }
    var summary = node("section", null, "form-summary");
    summary.appendChild(node("h2", "What you're looking at"));
    summary.appendChild(node("p", "Four deterministic profile variants are derived from the same exact Part placements: neutral, wider/softer, narrower/readable, and selected depth-forward tuning."));
    summary.appendChild(node("p", "Front is x/y, side is z/y, and top is x/z. The tail is straight in these placements. The gallery draws overlapping filled primitives only."));
    summary.appendChild(node("p", "This does not claim surface continuity, anatomical correctness, mesh or topology, rigging, animation/IK, deformation, physics, runtime behaviour, or Readiness 3."));
    app.appendChild(summary);
    app.appendChild(provisionalFormPreviewSection(payload));
    var metadata = node("section", null, "structure-header form-metadata");
    metadata.appendChild(node("p", "Provisional filled-form inspection", "structure-kicker"));
    metadata.appendChild(metadataGrid([
      ["Status", payload.status], ["Stage", payload.stage], ["Source identity", String(payload.source.namespace) + " / " + String(payload.source.document)],
      ["Resource profile", payload.source.resource_profile_id], ["Reference scale", "edge " + payload.reference_scale.parent.role + " → " + payload.reference_scale.child.role + " · squared length " + payload.reference_scale.squared_length],
      ["Projection format", payload.format], ["Variants", String(payload.variants.length) + " fixed profiles"]
    ]));
    metadata.appendChild(node("p", "Developer appraisal candidate only. Display radii and extents are the descriptor permille values multiplied by the square root of the reference squared length.", "disclaimer"));
    app.appendChild(metadata);
    var raw = node("details", null, "form-raw");
    raw.appendChild(node("summary", "Raw provisional-form JSON"));
    raw.appendChild(node("pre", jsonText(payload), "context-json"));
    app.appendChild(raw);
  }

  function renderStructure(rawStructure, review) {
    clear(app);
    var structure = rawStructure;
    var title = review && review.title ? String(review.title) : "Structural inspection";
    document.title = title;
    var back = node("a", "← All reviews", "back-link");
    back.href = "/";
    app.appendChild(back);
    app.appendChild(node("h1", title));
    app.appendChild(node("code", "read-only", "stable-id"));
    if (review && review.description) {
      app.appendChild(node("p", review.description, "lede"));
    }
    if (review && review.instructions) {
      var instructions = node("aside", null, "instructions");
      instructions.appendChild(node("h2", "Instructions"));
      instructions.appendChild(node("p", review.instructions));
      app.appendChild(instructions);
    }
    var spatialPanel = spatialPreviewSection(structure);
    if (spatialPanel) {
      app.appendChild(spatialPanel);
    }
    var preparedPanel = preparedSourceSection(structure);
    if (preparedPanel) {
      app.appendChild(preparedPanel);
    }
    var guidance = node("aside", null, "instructions");
    guidance.appendChild(node("h2", "What to inspect"));
    guidance.appendChild(node("p", "Check that the authored creature structure matches its intent before later stages generate geometry or runtime behaviour."));
    var checklist = node("ul");
    [
      "Expected parts are present once, use the intended side or other anchors, and sit under the correct parent.",
      "Joints connect the intended proximal and distal parts.",
      "Modules, sockets, attachments, regions, and capabilities group the intended subjects."
    ].forEach(function (item) { checklist.appendChild(node("li", item)); });
    guidance.appendChild(checklist);
    guidance.appendChild(node("p", "Do not judge appearance, mesh quality, animation, IK, deformation, or physics here; this view generates none of them.", "muted"));
    app.appendChild(guidance);
    var graph = isObject(structure) && isObject(structure.graph) ? structure.graph : {};
    var source = isObject(graph.source) ? graph.source : {};
    var contract = isObject(graph.contract) ? graph.contract : {};
    var basis = isObject(graph.basis) ? graph.basis : {};
    var header = node("section", null, "structure-header");
    header.appendChild(node("p", "Provisional structural inspection", "structure-kicker"));
    header.appendChild(metadataGrid([
      ["Status", isObject(structure) && structure.status !== undefined ? structure.status : "Invalid payload"],
      ["Stage", isObject(structure) && structure.stage !== undefined ? structure.stage : "Unavailable"],
      ["Source identity", source.namespace !== undefined || source.document !== undefined ? String(source.namespace || "?") + " / " + String(source.document || "?") : "Unavailable"],
      ["Contract", contract.family !== undefined ? String(contract.family) + " r" + String(contract.revision === undefined ? "?" : contract.revision) : "Unavailable"],
      ["Basis", Object.keys(basis).length ? jsonText(basis) : "Unavailable"],
      ["Projection format", (isObject(structure) && structure.format) || "Unavailable"],
      ["Projection", graph.projection || "Unavailable"]
    ]));
    header.appendChild(node("p", "Provisional, source-preserving debug projection. No geometry is rendered or implied, and this view does not represent runtime state.", "disclaimer"));
    app.appendChild(header);

    var validationErrors = validateStructure(structure);
    if (!isObject(structure) || structure.status !== "success" || validationErrors.length) {
      app.appendChild(diagnosticsBlock(structure, validationErrors));
      if (isObject(structure)) {
        app.appendChild(valueDetails("Raw structural JSON", structure));
      }
      return;
    }

    var counts = node("section", null, "structure-section count-section");
    counts.appendChild(node("h2", "Collections"));
    counts.appendChild(node("p", "Counts are direct collection cardinalities in this projection; zero is a valid result."));
    counts.appendChild(metadataGrid([
      ["Modules", collectionCount(graph.modules)], ["Parts", collectionCount(graph.parts)], ["Joints", collectionCount(graph.joints)],
      ["Sockets", collectionCount(graph.sockets)], ["Attachments", collectionCount(graph.attachments)], ["Landmarks", collectionCount(graph.landmarks)],
      ["Dimensions", collectionCount(graph.dimensions)], ["Frames", collectionCount(graph.frames)], ["Regions", collectionCount(graph.regions)],
      ["Capabilities", collectionCount(graph.capabilities)], ["Fields", collectionCount(graph.fields)]
    ]));
    app.appendChild(counts);
    app.appendChild(containmentSection(graph));
    app.appendChild(jointSection(graph));
    app.appendChild(simpleCollectionSection("Composition — modules, sockets, and attachments", [
      { label: "Modules", items: graph.modules }, { label: "Sockets", items: graph.sockets }, { label: "Attachments", items: graph.attachments }
    ], "Attachments compose module placement; they do not themselves imply articulation. Joints are shown separately above."));
    app.appendChild(regionsCapabilitiesSection(graph));
    app.appendChild(simpleCollectionSection("Other structural collections", [
      { label: "Landmarks", items: graph.landmarks }, { label: "Dimensions", items: graph.dimensions }, { label: "Frames", items: graph.frames }, { label: "Fields", items: graph.fields }
    ]));
    app.appendChild(valueDetails("Raw structural JSON", structure));
  }

  function openImage(items, selectedIndex) {
    var returnFocus = document.activeElement;
    var dialog = node("dialog", null, "image-dialog");
    var heading = node("h2", "Image comparison", "image-dialog-title");
    heading.id = "image-dialog-title";
    dialog.setAttribute("aria-labelledby", "image-dialog-title");
    var header = node("header", null, "image-dialog-header");
    header.appendChild(heading);

    var controls = node("div", null, "image-dialog-controls");
    var previous = node("button", "Previous", "image-control image-navigation-control");
    previous.type = "button";
    previous.setAttribute("aria-label", "Show previous image");
    var next = node("button", "Next", "image-control image-navigation-control");
    next.type = "button";
    next.setAttribute("aria-label", "Show next image");
    var zoomOut = node("button", "Zoom out", "image-control");
    zoomOut.type = "button";
    zoomOut.setAttribute("aria-label", "Zoom out of image");
    var zoomIn = node("button", "Zoom in", "image-control");
    zoomIn.type = "button";
    zoomIn.setAttribute("aria-label", "Zoom in on image");
    var fit = node("button", "Fit / reset", "image-control");
    fit.type = "button";
    fit.setAttribute("aria-label", "Fit image to viewport and reset zoom");
    var scaleLabel = node("span", "Scale: —", "image-scale");
    scaleLabel.setAttribute("aria-live", "polite");
    var positionLabel = node("span", "Item: —", "image-position");
    positionLabel.setAttribute("aria-live", "polite");
    positionLabel.setAttribute("role", "status");
    controls.appendChild(previous);
    controls.appendChild(next);
    controls.appendChild(zoomOut);
    controls.appendChild(zoomIn);
    controls.appendChild(fit);
    controls.appendChild(scaleLabel);
    controls.appendChild(positionLabel);

    var close = node("button", "Close", "close-dialog");
    close.type = "button";
    close.setAttribute("aria-label", "Close image viewer");
    header.appendChild(controls);
    header.appendChild(close);
    dialog.appendChild(header);

    var viewport = node("div", null, "image-viewport");
    viewport.tabIndex = 0;
    viewport.setAttribute("role", "region");
    viewport.setAttribute("aria-label", "Scrollable image viewport");
    var canvas = node("div", null, "image-canvas");
    var image = node("img");
    canvas.appendChild(image);
    viewport.appendChild(canvas);
    dialog.appendChild(viewport);
    dialog.appendChild(node("p", "Use Previous/Next, the Left/Right arrow keys, or click the displayed image to compare items. Escape closes the viewer.", "image-dialog-instructions"));

    var MIN_SCALE = 0.1;
    var MAX_SCALE = 8;
    var ZOOM_FACTOR = 1.25;
    var scale = 1;
    var fitScale = 1;
    var cleaned = false;
    var currentIndex = Math.max(0, Math.min(items.length - 1, selectedIndex || 0));
    var imageLoadToken = 0;
    var releaseScrollLock = acquireImageDialogLock();

    function imageSize() {
      return { width: image.naturalWidth || 1, height: image.naturalHeight || 1 };
    }

    function updateScaleLabel() {
      scaleLabel.textContent = "Scale: " + (scale * 100).toFixed(1) + "%";
    }

    function renderCanvas() {
      var size = imageSize();
      var imageWidth = size.width * scale;
      var imageHeight = size.height * scale;
      var canvasWidth = Math.max(viewport.clientWidth, imageWidth);
      var canvasHeight = Math.max(viewport.clientHeight, imageHeight);
      canvas.style.width = canvasWidth + "px";
      canvas.style.height = canvasHeight + "px";
      image.style.width = size.width + "px";
      image.style.height = size.height + "px";
      image.style.left = Math.max(0, (canvasWidth - imageWidth) / 2) + "px";
      image.style.top = Math.max(0, (canvasHeight - imageHeight) / 2) + "px";
      image.style.transform = "scale(" + scale + ")";
      updateScaleLabel();
    }

    function clampScale(value) {
      return Math.max(MIN_SCALE, Math.min(MAX_SCALE, value));
    }

    function fitToViewport() {
      var size = imageSize();
      var width = viewport.clientWidth || size.width;
      var height = viewport.clientHeight || size.height;
      fitScale = Math.max(MIN_SCALE, Math.min(1, width / size.width, height / size.height));
      scale = fitScale;
      renderCanvas();
      viewport.scrollLeft = 0;
      viewport.scrollTop = 0;
    }

    function zoomTo(value, anchorX, anchorY) {
      var oldScale = scale;
      scale = clampScale(value);
      if (scale === oldScale) {
        return;
      }
      renderCanvas();
      if (anchorX !== undefined && anchorY !== undefined) {
        var ratio = scale / oldScale;
        viewport.scrollLeft = Math.max(0, anchorX * ratio - (anchorX - viewport.scrollLeft));
        viewport.scrollTop = Math.max(0, anchorY * ratio - (anchorY - viewport.scrollTop));
      }
    }

    function zoomBy(factor) {
      zoomTo(scale * factor, viewport.scrollLeft + viewport.clientWidth / 2, viewport.scrollTop + viewport.clientHeight / 2);
    }

    function onWheel(event) {
      event.preventDefault();
      event.stopPropagation();
      var rect = viewport.getBoundingClientRect();
      var anchorX = event.clientX - rect.left + viewport.scrollLeft;
      var anchorY = event.clientY - rect.top + viewport.scrollTop;
      zoomTo(scale * (event.deltaY < 0 ? ZOOM_FACTOR : 1 / ZOOM_FACTOR), anchorX, anchorY);
    }

    function onKeyDown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeImageDialog();
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        showItem(currentIndex - 1, document.activeElement === image);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        showItem(currentIndex + 1, document.activeElement === image);
      } else if (event.key === "+" || event.key === "=" || event.key === "Add") {
        event.preventDefault();
        zoomBy(ZOOM_FACTOR);
      } else if (event.key === "-" || event.key === "_" || event.key === "Subtract") {
        event.preventDefault();
        zoomBy(1 / ZOOM_FACTOR);
      }
    }

    function onResize() {
      fitToViewport();
    }

    function showItem(index, focusImage) {
      if (!items.length) {
        return;
      }
      currentIndex = (index + items.length) % items.length;
      var item = items[currentIndex];
      var loadToken = ++imageLoadToken;
      var nextImage = node("img");
      nextImage.alt = item.title;
      nextImage.title = item.title;
      nextImage.tabIndex = 0;
      nextImage.setAttribute("role", "button");
      nextImage.setAttribute("aria-label", "Show next comparison image");
      function showNextImage(event) {
        if (event.type === "keydown" && event.key !== "Enter" && event.key !== " ") {
          return;
        }
        if (event.type === "keydown") {
          event.preventDefault();
        }
        showItem(currentIndex + 1, true);
      }
      nextImage.addEventListener("click", showNextImage);
      nextImage.addEventListener("keydown", showNextImage);
      nextImage.addEventListener("load", function () {
        if (cleaned || loadToken !== imageLoadToken || image !== nextImage) {
          return;
        }
        fitToViewport();
      });
      canvas.replaceChild(nextImage, image);
      image = nextImage;
      image.src = item.source;
      if (focusImage) {
        image.focus();
      }
      heading.textContent = item.title;
      positionLabel.textContent = "Item " + (currentIndex + 1) + " of " + items.length + ": " + item.title;
      previous.disabled = items.length < 2;
      next.disabled = items.length < 2;
      fitToViewport();
    }

    function cleanup() {
      if (cleaned) {
        return;
      }
      cleaned = true;
      releaseScrollLock();
      window.removeEventListener("resize", onResize);
      viewport.removeEventListener("wheel", onWheel);
      dialog.removeEventListener("keydown", onKeyDown);
      dialog.remove();
      if (returnFocus && returnFocus.focus && document.documentElement.contains(returnFocus)) {
        returnFocus.focus();
      }
    }

    function closeImageDialog() {
      if (cleaned) {
        return;
      }
      if (dialog.open) {
        dialog.close();
      }
      cleanup();
    }

    close.addEventListener("click", closeImageDialog);
    previous.addEventListener("click", function () { showItem(currentIndex - 1); });
    next.addEventListener("click", function () { showItem(currentIndex + 1); });
    zoomOut.addEventListener("click", function () { zoomBy(1 / ZOOM_FACTOR); });
    zoomIn.addEventListener("click", function () { zoomBy(ZOOM_FACTOR); });
    fit.addEventListener("click", fitToViewport);
    viewport.addEventListener("wheel", onWheel, { passive: false });
    dialog.addEventListener("keydown", onKeyDown);
    dialog.addEventListener("cancel", function (event) {
      event.preventDefault();
      closeImageDialog();
    });
    dialog.addEventListener("close", cleanup);
    document.body.appendChild(dialog);
    try {
      dialog.showModal();
    } catch (error) {
      cleanup();
      throw error;
    }
    window.addEventListener("resize", onResize);
    showItem(currentIndex);
    updateScaleLabel();
  }

  function renderReview(data) {
    document.title = "Creature Kernel visual review";
    if (data && data.kind === "provisional-form") {
      renderProvisionalForm(data.provisional_form, data);
      return;
    }
    if (data && data.kind === "structure") {
      renderStructure(data.structure, data);
      return;
    }
    var review = data && data.review ? data.review : data;
    if (review && review.kind === "provisional-form") {
      renderProvisionalForm(review.provisional_form, review);
      return;
    }
    if (review && review.kind === "structure") {
      renderStructure(review.structure, review);
      return;
    }
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
      var imageItems = group.items.map(function (groupItem) {
        var imageItem = {};
        Object.keys(groupItem).forEach(function (key) { imageItem[key] = groupItem[key]; });
        imageItem.source = "/api/reviews/" + encodeURIComponent(review.id) + "/assets/" + groupItem.image.substring("assets/".length).split("/").map(encodeURIComponent).join("/");
        return imageItem;
      });
      var selected = (oldResponse && oldResponse.selections[group.id]) || [];
      group.items.forEach(function (item, itemIndex) {
        var card = node("article", null, "option-card");
        var imageButton = node("button", null, "image-button");
        imageButton.type = "button";
        imageButton.setAttribute("aria-label", "Expand " + item.title);
        var image = node("img");
        image.src = imageItems[itemIndex].source;
        image.alt = item.title;
        image.loading = "lazy";
        imageButton.appendChild(image);
        imageButton.addEventListener("click", function () { openImage(imageItems, itemIndex); });
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
