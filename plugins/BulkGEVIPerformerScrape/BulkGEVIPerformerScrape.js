(() => {
  const { React, ReactDOM, patch } = PluginApi;
  const h = React.createElement;
  const PLUGIN_ID = "BulkGEVIPerformerScrape";
  const TASK_NAME = "Scrape selected performers";

  const FIELD_GROUPS = [
    ["Identity", [
      ["name", "Name"],
      ["disambiguation", "Disambiguation"],
      ["aliases", "Aliases"],
      ["gender", "Gender"],
      ["urls", "GEVI URL (merge only)"],
      ["image", "Image"],
    ]],
    ["Physical", [
      ["hair_color", "Hair color"],
      ["eye_color", "Eye color"],
      ["height", "Height"],
      ["weight", "Weight"],
      ["ethnicity", "Ethnicity"],
      ["country", "Country"],
      ["circumcised", "Circumcision"],
      ["penis_length", "Penis length"],
      ["tattoos", "Tattoos"],
    ]],
    ["Biography", [
      ["birthdate", "Birth year"],
      ["death_date", "Death year"],
      ["details", "Details / notes"],
    ]],
  ];

  async function gql(query, variables) {
    const response = await fetch("/graphql", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, variables }),
    });
    const result = await response.json();
    if (!response.ok || result.errors) {
      throw new Error((result.errors || []).map((x) => x.message).join("; ") || response.statusText);
    }
    return result.data;
  }

  function closeModal(node) {
    try { ReactDOM.unmountComponentAtNode(node); } catch (_) {}
    node.remove();
  }

  function Modal({ selectedIds, host }) {
    const [fields, setFields] = React.useState([]);
    const [mergeAliases, setMergeAliases] = React.useState(true);
    const [tagSkipped, setTagSkipped] = React.useState(true);
    const [removeSkipped, setRemoveSkipped] = React.useState(true);
    const [submitting, setSubmitting] = React.useState(false);
    const [error, setError] = React.useState("");

    const toggleField = (field) => {
      setFields((current) => current.includes(field)
        ? current.filter((x) => x !== field)
        : [...current, field]);
    };

    const submit = async () => {
      if (!fields.length) {
        setError("Select at least one field. The plugin refuses to perform an impressively efficient no-op.");
        return;
      }
      setSubmitting(true);
      setError("");
      try {
        const mutation = `mutation Run($plugin_id: ID!, $task_name: String!, $args_map: Map) {
          runPluginTask(plugin_id: $plugin_id, task_name: $task_name, args_map: $args_map)
        }`;
        const data = await gql(mutation, {
          plugin_id: PLUGIN_ID,
          task_name: TASK_NAME,
          args_map: {
            performer_ids: Array.from(selectedIds),
            options: {
              fields,
              merge_aliases: mergeAliases,
              tag_skipped: tagSkipped,
              remove_skipped_on_success: removeSkipped,
            },
          },
        });
        closeModal(host);
        window.alert(`Bulk GEVI scrape started as job ${data.runPluginTask}. Progress and results are in Tasks / logs.`);
      } catch (e) {
        setError(e.message || String(e));
        setSubmitting(false);
      }
    };

    const checkbox = (id, label, checked, onChange, disabled = false) =>
      h("div", { className: "form-check", key: id },
        h("input", { className: "form-check-input", type: "checkbox", id, checked, disabled, onChange }),
        h("label", { className: "form-check-label", htmlFor: id }, label)
      );

    return h("div", { className: "modal fade show", style: { display: "block", background: "rgba(0,0,0,.68)" }, role: "dialog" },
      h("div", { className: "modal-dialog modal-lg modal-dialog-scrollable" },
        h("div", { className: "modal-content" },
          h("div", { className: "modal-header" },
            h("h5", { className: "modal-title" }, `Bulk GEVI Performer Scrape — ${selectedIds.size} selected`),
            h("button", { type: "button", className: "close btn-close", disabled: submitting, onClick: () => closeModal(host) })
          ),
          h("div", { className: "modal-body" },
            h("p", null, "Every metadata field is off by default. Existing GEVI URLs are used directly; name searches must return exactly one exact match."),
            error && h("div", { className: "alert alert-danger" }, error),
            h("div", { className: "row" }, FIELD_GROUPS.map(([title, group]) =>
              h("div", { className: "col-md-4", key: title },
                h("h6", null, title),
                ...group.map(([field, label]) => checkbox(`gevi-${field}`, label, fields.includes(field), () => toggleField(field)))
              )
            )),
            h("hr"),
            checkbox("gevi-merge-aliases", "Merge aliases instead of replacing them", mergeAliases, (e) => setMergeAliases(e.target.checked), !fields.includes("aliases")),
            checkbox("gevi-tag-skipped", 'Apply "GEVI: Skipped Performer" when ambiguous or unmatched', tagSkipped, (e) => setTagSkipped(e.target.checked)),
            checkbox("gevi-remove-skipped", "Remove the skipped tag after a successful scrape", removeSkipped, (e) => setRemoveSkipped(e.target.checked), !tagSkipped)
          ),
          h("div", { className: "modal-footer" },
            h("button", { className: "btn btn-secondary", disabled: submitting, onClick: () => closeModal(host) }, "Cancel"),
            h("button", { className: "btn btn-primary", disabled: submitting || !fields.length, onClick: submit }, submitting ? "Starting…" : "Scrape selected performers")
          )
        )
      )
    );
  }

  function openModal(selectedIds) {
    const host = document.createElement("div");
    host.id = "bulk-gevi-performer-scrape-modal";
    document.body.appendChild(host);
    ReactDOM.render(h(Modal, { selectedIds: new Set(selectedIds), host }), host);
  }

  patch.before("FilteredPerformerList", (props) => {
    const next = { ...(props || {}) };
    const current = Array.isArray(next.extraOperations) ? next.extraOperations.slice() : [];
    current.push({
      text: "Scrape selected with GEVI…",
      isDisplayed: (_result, _filter, selectedIds) => selectedIds && selectedIds.size > 0,
      onClick: (_result, _filter, selectedIds) => openModal(selectedIds),
    });
    next.extraOperations = current;
    return [next];
  });
})();
