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
    document.title = "Creature Kernel visual reviews";
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
      if (session.kind === "structure") {
        card.appendChild(node("span", "Structural inspection", "session-kind"));
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
    document.title = "Creature Kernel visual review";
    if (data && data.kind === "structure") {
      renderStructure(data.structure, data);
      return;
    }
    var review = data && data.review ? data.review : data;
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
