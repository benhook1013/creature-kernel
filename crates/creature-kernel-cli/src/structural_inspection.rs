//! Provisional developer-facing structural inspection adapter.
//!
//! This is deliberately a thin CLI boundary around the active Readiness 2
//! admission function and the preparatory structural validator.  Its graph is
//! a source-preserving debug projection, not a resolver or finalized snapshot.

use creature_kernel_core::body_document::{
    Diagnostic, ResourceProfile, Status, admit_body_document,
};
use creature_kernel_core::body_graph::StructuralBodyGraph;
use creature_kernel_core::provisional_json::{self, Map, Number, Value, json};
use creature_kernel_core::semantic_address::AddressKey;
use creature_kernel_core::structural_validation::{
    StructuralDiagnostic, validate_structural_body_document,
};
use std::cmp::Ordering;
use std::io::{self, Read};
use std::path::Path;

const FORMAT: &str = "creature-kernel.provisional-structural-inspection.v1";

/// Serialized result and process status for one CLI invocation.
#[derive(Debug, PartialEq)]
pub(crate) struct CliResult {
    pub json: String,
    pub exit_code: i32,
}

/// Run the command-line adapter over process arguments after the executable.
pub(crate) fn run_cli<I, S>(arguments: I) -> CliResult
where
    I: IntoIterator<Item = S>,
    S: Into<String>,
{
    let arguments: Vec<String> = arguments.into_iter().map(Into::into).collect();
    if let Some(help) = help_response(&arguments) {
        return result(help);
    }
    let Some(input) = parse_input_path(&arguments) else {
        return result(usage_error(
            "usage: creature-kernel inspect-structure --input <path> (use '-' for stdin)",
        ));
    };

    let source = match read_input(input) {
        Ok(source) => source,
        Err(error) => return result(input_error(error.to_string())),
    };

    inspect_source(&source)
}

fn help_response(arguments: &[String]) -> Option<Value> {
    let (operation, usage, description) = match arguments {
        [flag] if flag == "--help" || flag == "-h" => (
            "help",
            "creature-kernel inspect-structure --input <path> (use '-' for stdin)",
            "Inspect an admitted body document and emit its structural projection.",
        ),
        [command, flag] if command == "inspect-structure" && (flag == "--help" || flag == "-h") => {
            (
                "inspect-structure",
                "creature-kernel inspect-structure --input <path> (use '-' for stdin)",
                "Inspect an admitted body document and emit its structural projection.",
            )
        }
        _ => return None,
    };

    let mut output = base_output("help");
    output.insert("operation".to_owned(), Value::String(operation.to_owned()));
    output.insert("status".to_owned(), Value::String("success".to_owned()));
    output.insert("processing_complete".to_owned(), Value::Bool(true));
    output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
    output.insert("diagnostics".to_owned(), Value::Array(Vec::new()));
    let mut help = json!({
        "usage": usage,
        "description": description,
        "options": [
            {"flag": "--input <path>", "description": "Read a body document from a file (use '-' for stdin)."},
            {"flag": "--help", "description": "Show this structured help response."}
        ]
    });
    if operation == "help"
        && let Value::Object(help) = &mut help
    {
        help.insert(
            "commands".to_owned(),
            json!([
                {
                    "command": "inspect-structure",
                    "usage": "creature-kernel inspect-structure --input <path> (use '-' for stdin)",
                    "description": "Inspect an admitted body document and emit its structural projection."
                },
                {
                    "command": "inspect-prepared-source",
                    "usage": "creature-kernel inspect-prepared-source --input <path> (use '-' for stdin)",
                    "description": "Inspect bounded source preparation and emit its provisional debug projection."
                },
                {
                    "command": "inspect-provisional-form",
                    "usage": "creature-kernel inspect-provisional-form --input <path> (use '-' for stdin)",
                    "description": "Inspect four fixed display-only provisional filled-form variants."
                }
            ]),
        );
    }
    output.insert("help".to_owned(), help);
    Some(Value::Object(output))
}

pub(crate) fn read_input(input: &Path) -> io::Result<Vec<u8>> {
    if input == Path::new("-") {
        let stdin = io::stdin();
        read_bounded(stdin.lock())
    } else {
        read_bounded(std::fs::File::open(input)?)
    }
}

pub(crate) fn read_bounded<R: Read>(reader: R) -> io::Result<Vec<u8>> {
    let mut source = Vec::new();
    reader
        .take((creature_kernel_core::body_document::ORDINARY_MAX_SOURCE_BYTES + 1) as u64)
        .read_to_end(&mut source)?;
    Ok(source)
}

fn parse_input_path(arguments: &[String]) -> Option<&Path> {
    if arguments.first().map(String::as_str) != Some("inspect-structure") {
        return None;
    }

    let mut input = None;
    let mut index = 1;
    while index < arguments.len() {
        if arguments[index] != "--input" || input.is_some() {
            return None;
        }
        index += 1;
        let value = arguments.get(index)?;
        if value.starts_with('-') && value != "-" {
            return None;
        }
        input = Some(Path::new(value));
        index += 1;
    }
    input
}

/// Inspect already-acquired source bytes.  Keeping this separate from file
/// acquisition makes the output and exit contract straightforward to test.
pub(crate) fn inspect_source(source: &[u8]) -> CliResult {
    let admission = admit_body_document(source, ResourceProfile::ORDINARY);
    let mut output = base_output("admission");
    output.insert(
        "status".to_owned(),
        Value::String(status_name(admission.status).to_owned()),
    );
    output.insert(
        "processing_complete".to_owned(),
        Value::Bool(admission.processing_complete),
    );
    output.insert(
        "diagnostics_complete".to_owned(),
        Value::Bool(admission.diagnostics_complete),
    );
    output.insert(
        "diagnostics".to_owned(),
        Value::Array(
            admission
                .diagnostics
                .iter()
                .map(admission_diagnostic)
                .collect(),
        ),
    );
    if let Some(primary) = admission.primary_diagnostic.as_ref() {
        output.insert(
            "primary_diagnostic".to_owned(),
            admission_diagnostic(primary),
        );
    }

    if admission.status != Status::Success {
        return result(Value::Object(output));
    }

    let Some(document) = admission.document.as_ref() else {
        output.insert(
            "status".to_owned(),
            Value::String("internal-failure".to_owned()),
        );
        output.insert("stage".to_owned(), Value::String("admission".to_owned()));
        output.insert(
            "diagnostics".to_owned(),
            json!([cli_diagnostic(
                "ck.cli.missing-admitted-document",
                "admission reported success without a document"
            )]),
        );
        return result(Value::Object(output));
    };

    let structural = validate_structural_body_document(document);
    output.insert(
        "stage".to_owned(),
        Value::String("structural-validation".to_owned()),
    );
    // Admission succeeded and the bounded structural validator has now run
    // all of its checks and retained all diagnostics.  These are overall
    // operation fields, not admission-only values.
    output.insert("processing_complete".to_owned(), Value::Bool(true));
    output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
    output.insert(
        "diagnostics".to_owned(),
        Value::Array(
            structural
                .diagnostics
                .iter()
                .map(structural_diagnostic)
                .collect(),
        ),
    );
    if let Some(primary) = structural.diagnostics.first() {
        output.insert(
            "primary_diagnostic".to_owned(),
            structural_diagnostic(primary),
        );
    }
    match structural.graph {
        Some(graph) if structural.diagnostics.is_empty() => {
            output.insert("status".to_owned(), Value::String("success".to_owned()));
            output.insert("summary".to_owned(), graph_summary(&graph));
            output.insert("graph".to_owned(), graph_projection(&graph));
            result(Value::Object(output))
        }
        _ => {
            // Structural errors are source-caused failures.  The core
            // admission status remains unchanged; this adapter reports the
            // operation outcome at the structural stage.
            output.insert(
                "status".to_owned(),
                Value::String("invalid-source".to_owned()),
            );
            result(Value::Object(output))
        }
    }
}

fn graph_summary(graph: &StructuralBodyGraph) -> Value {
    // Keep this summary flat and compact so callers can inspect cardinality
    // without traversing the full source-preserving projection. The graph's
    // BTreeMap-backed collections make these counts deterministic.
    json!({
        "modules": graph.modules().len(),
        "parts": graph.parts().len(),
        "joints": graph.joints().len(),
        "sockets": graph.sockets().len(),
        "attachments": graph.attachments().len(),
        "landmarks": graph.landmarks().len(),
        "dimensions": graph.dimensions().len(),
        "frames": graph.frames().len(),
        "regions": graph.regions().len(),
        "capabilities": graph.capabilities().len(),
        "fields": graph.fields().len()
    })
}

fn result(value: Value) -> CliResult {
    let exit_code = if value.get("status") == Some(&Value::String("success".to_owned())) {
        0
    } else {
        1
    };
    CliResult {
        json: provisional_json::to_string(&value).unwrap_or_else(|_| {
            // All values in this adapter are provisional_json::Value, so this is a
            // defensive fallback for a future change rather than an ordinary
            // input failure path.
            r#"{"format":"creature-kernel.provisional-structural-inspection.v1","operation":"inspect-structure","status":"internal-failure","stage":"output","diagnostics":[{"code":"ck.cli.output-serialization","message":"could not serialize inspection result"}]}"#.to_owned()
        }),
        exit_code,
    }
}

fn base_output(stage: &str) -> Map<String, Value> {
    Map::from_iter([
        ("format".to_owned(), Value::String(FORMAT.to_owned())),
        (
            "operation".to_owned(),
            Value::String("inspect-structure".to_owned()),
        ),
        ("stage".to_owned(), Value::String(stage.to_owned())),
    ])
}

fn usage_error(message: &str) -> Value {
    let mut output = base_output("usage");
    output.insert("status".to_owned(), Value::String("usage-error".to_owned()));
    output.insert("processing_complete".to_owned(), Value::Bool(false));
    output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
    output.insert(
        "diagnostics".to_owned(),
        json!([cli_diagnostic("ck.cli.usage", message)]),
    );
    Value::Object(output)
}

fn input_error(message: String) -> Value {
    let mut output = base_output("input");
    output.insert(
        "status".to_owned(),
        Value::String("input-failure".to_owned()),
    );
    output.insert("processing_complete".to_owned(), Value::Bool(false));
    output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
    output.insert(
        "diagnostics".to_owned(),
        json!([cli_diagnostic("ck.cli.input-read", message)]),
    );
    Value::Object(output)
}

fn cli_diagnostic(code: &str, message: impl Into<String>) -> Value {
    json!({
        "code": code,
        "message": message.into(),
        "instance_path": Value::Null,
        "schema_path": Value::Null,
    })
}

fn admission_diagnostic(diagnostic: &Diagnostic) -> Value {
    json!({
        "code": diagnostic.code,
        "message": diagnostic.message,
        "instance_path": diagnostic.instance_path,
        "schema_path": diagnostic.schema_path,
    })
}

fn structural_diagnostic(diagnostic: &StructuralDiagnostic) -> Value {
    json!({
        "category": diagnostic.category.as_str(),
        "code": diagnostic.code,
        "address": diagnostic.address.as_ref().map(address_key_value),
        "role": diagnostic.role,
        "detail": diagnostic.detail,
    })
}

pub(crate) fn address_key_value(address: &AddressKey) -> Value {
    json!({
        "namespace": address.namespace(),
        "anchors": address.anchors(),
        "kind": creature_kernel_core::semantic_address::kind_name(address.kind()),
        "role": address.role(),
    })
}

fn status_name(status: Status) -> &'static str {
    match status {
        Status::Success => "success",
        Status::InvalidSource => "invalid-source",
        Status::Unsupported => "unsupported",
        Status::ResourceLimit => "resource-limit",
        Status::InternalFailure => "internal-failure",
    }
}

pub(crate) fn graph_projection(graph: &StructuralBodyGraph) -> Value {
    // BTreeMap::values() is intentional: its order is the structural key
    // order, independent of source collection permutation.
    let mut source = graph.source().clone();
    source.dependencies.sort_by(|left, right| {
        left.namespace
            .cmp(&right.namespace)
            .then_with(|| left.document.cmp(&right.document))
            .then_with(|| left.content_sha256.cmp(&right.content_sha256))
    });

    let mut extensions = graph.extensions().to_vec();
    extensions.sort_by(|left, right| {
        left.namespace
            .cmp(&right.namespace)
            .then_with(|| numeric_revision_cmp(&left.revision, &right.revision))
            .then_with(|| left.required.cmp(&right.required))
            .then_with(|| {
                deterministic_json(&left.payload).cmp(&deterministic_json(&right.payload))
            })
    });

    let regions = graph
        .regions()
        .values()
        .map(|region| {
            let mut region = region.clone();
            region.parts.sort_by(compare_addresses);
            region
        })
        .collect::<Vec<_>>();
    let capabilities = graph
        .capabilities()
        .values()
        .map(|capability| {
            let mut capability = capability.clone();
            capability.subjects.sort_by(compare_addresses);
            capability
        })
        .collect::<Vec<_>>();

    json!({
        "projection": "source-preserving-provisional-structural-debug",
        "contract": graph.contract(),
        "source": source,
        "basis": graph.basis(),
        "profiles": graph.profiles(),
        "extensions": extensions,
        "modules": graph.modules().values().collect::<Vec<_>>(),
        "parts": graph.parts().values().collect::<Vec<_>>(),
        "joints": graph.joints().values().collect::<Vec<_>>(),
        "sockets": graph.sockets().values().collect::<Vec<_>>(),
        "attachments": graph.attachments().values().collect::<Vec<_>>(),
        "landmarks": graph.landmarks().values().collect::<Vec<_>>(),
        "dimensions": graph.dimensions().values().collect::<Vec<_>>(),
        "frames": graph.frames().values().collect::<Vec<_>>(),
        "regions": regions,
        "capabilities": capabilities,
        "fields": graph.fields().values().collect::<Vec<_>>(),
    })
}

fn numeric_revision_cmp(left: &Number, right: &Number) -> Ordering {
    let left_text = left.to_string();
    let right_text = right.to_string();
    match (
        positive_integer_digits(&left_text),
        positive_integer_digits(&right_text),
    ) {
        (Some(left_digits), Some(right_digits)) => left_digits
            .len()
            .cmp(&right_digits.len())
            .then_with(|| left_digits.cmp(right_digits))
            .then_with(|| left_text.cmp(&right_text)),
        _ => left_text.cmp(&right_text),
    }
}

fn positive_integer_digits(value: &str) -> Option<&str> {
    if value.is_empty() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    let digits = value.trim_start_matches('0');
    Some(if digits.is_empty() { "0" } else { digits })
}

fn deterministic_json(value: &Value) -> String {
    match value {
        Value::Null => "null".to_owned(),
        Value::Bool(value) => value.to_string(),
        Value::Number(value) => value.to_string(),
        Value::String(value) => provisional_json::to_string(value).expect("string serialization"),
        Value::Array(values) => {
            let values = values
                .iter()
                .map(deterministic_json)
                .collect::<Vec<_>>()
                .join(",");
            format!("[{values}]")
        }
        Value::Object(values) => {
            let mut entries = values.iter().collect::<Vec<_>>();
            entries.sort_by(|left, right| left.0.cmp(right.0));
            let values = entries
                .into_iter()
                .map(|(key, value)| {
                    format!(
                        "{}:{}",
                        provisional_json::to_string(key).expect("object-key serialization"),
                        deterministic_json(value)
                    )
                })
                .collect::<Vec<_>>()
                .join(",");
            format!("{{{values}}}")
        }
    }
}

fn compare_addresses(
    left: &creature_kernel_core::body_document::Address,
    right: &creature_kernel_core::body_document::Address,
) -> Ordering {
    match (AddressKey::try_from(left), AddressKey::try_from(right)) {
        (Ok(left), Ok(right)) => left.cmp(&right),
        _ => left
            .namespace
            .cmp(&right.namespace)
            .then_with(|| left.anchors.cmp(&right.anchors))
            .then_with(|| {
                creature_kernel_core::semantic_address::kind_rank(&left.kind).cmp(
                    &creature_kernel_core::semantic_address::kind_rank(&right.kind),
                )
            })
            .then_with(|| left.role.cmp(&right.role)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use creature_kernel_core::provisional_json::Value;

    const HEADER: &str = r#"{
        "contract": {"family":"creature-kernel.body","revision":1},
        "source": {"document":"main","namespace":"main","dependencies":DEPENDENCIES},
        "basis": {"length_unit":"metre","handedness":"right","up":"+y","forward":"+z"},
        "profiles": {"semantic_numeric":"ck.numeric-frame.r1"},
        "body": {
            "modules":[],"parts":PARTS,"joints":[],"sockets":[],"attachments":[],
            "landmarks":[],"dimensions":[],"frames":[],"regions":REGIONS,
            "capabilities":CAPABILITIES,"fields":[]
        },
        "extensions":EXTENSIONS
    }"#;

    fn source(parts: &str) -> Vec<u8> {
        source_with(parts, "[]", "[]", "[]", "[]")
    }

    fn source_with(
        parts: &str,
        dependencies: &str,
        extensions: &str,
        regions: &str,
        capabilities: &str,
    ) -> Vec<u8> {
        HEADER
            .replace("PARTS", parts)
            .replace("DEPENDENCIES", dependencies)
            .replace("EXTENSIONS", extensions)
            .replace("REGIONS", regions)
            .replace("CAPABILITIES", capabilities)
            .into_bytes()
    }

    fn root(role: &str) -> String {
        format!(
            r#"{{"address":{{"namespace":"main","anchors":[],"kind":"part","role":"{role}"}},"containment":{{"root":true}},"placement":{{"translation":[0,0,0],"rotation_xyzw":[0,0,0,1]}}}}"#
        )
    }

    fn child(role: &str, parent: &str) -> String {
        format!(
            r#"{{"address":{{"namespace":"main","anchors":[],"kind":"part","role":"{role}"}},"containment":{{"parent":{{"namespace":"main","anchors":[],"kind":"part","role":"{parent}"}}}},"placement":{{"translation":[0,0,0],"rotation_xyzw":[0,0,0,1]}}}}"#
        )
    }

    fn address(kind: &str, role: &str) -> String {
        format!(r#"{{"namespace":"main","anchors":[],"kind":"{kind}","role":"{role}"}}"#)
    }

    fn part_reference(role: &str) -> String {
        address("part", role)
    }

    fn region(role: &str, parts: &str) -> String {
        format!(
            r#"{{"address":{},"parts":{}}}"#,
            address("region", role),
            parts
        )
    }

    fn capability(role: &str, subjects: &str) -> String {
        format!(
            r#"{{"address":{},"subjects":{}}}"#,
            address("capability", role),
            subjects
        )
    }

    fn dependency(namespace: &str, document: &str, digest_digit: char) -> String {
        format!(
            r#"{{"document":"{document}","namespace":"{namespace}","content_sha256":"sha256:{digest}"}}"#,
            digest = std::iter::repeat_n(digest_digit, 64).collect::<String>()
        )
    }

    fn extension(namespace: &str, revision: u64, payload: &str) -> String {
        format!(
            r#"{{"namespace":"{namespace}","revision":{revision},"required":false,"payload":{payload}}}"#
        )
    }

    fn inspect(parts: &str) -> (Value, i32) {
        let output = inspect_source(&source(parts));
        (
            provisional_json::from_str(&output.json).unwrap(),
            output.exit_code,
        )
    }

    #[test]
    fn structurally_valid_input_emits_graph_and_success() {
        let (output, exit_code) = inspect(&format!("[{}]", root("root")));
        assert_eq!(exit_code, 0);
        assert_eq!(output["status"], "success");
        assert_eq!(output["stage"], "structural-validation");
        assert_eq!(output["processing_complete"], true);
        assert_eq!(output["diagnostics_complete"], true);
        assert!(output["graph"].is_object());
        assert_eq!(output["graph"]["parts"].as_array().unwrap().len(), 1);
    }

    #[test]
    fn successful_output_includes_deterministic_collection_counts() {
        let output = inspect(&format!("[{}]", root("root"))).0;
        let summary = output["summary"].as_object().unwrap();
        let expected = [
            ("modules", 0),
            ("parts", 1),
            ("joints", 0),
            ("sockets", 0),
            ("attachments", 0),
            ("landmarks", 0),
            ("dimensions", 0),
            ("frames", 0),
            ("regions", 0),
            ("capabilities", 0),
            ("fields", 0),
        ];
        for (collection, count) in expected {
            assert_eq!(summary[collection], count, "missing or wrong {collection}");
        }
        assert!(
            output["graph"].is_object(),
            "summary must not replace graph"
        );
    }

    #[test]
    fn admitted_but_structurally_invalid_input_is_nonzero() {
        let (output, exit_code) = inspect(&format!("[{},{}]", root("a"), root("b")));
        assert_eq!(exit_code, 1);
        assert_eq!(output["status"], "invalid-source");
        assert_eq!(output["stage"], "structural-validation");
        assert_eq!(output["processing_complete"], true);
        assert_eq!(output["diagnostics_complete"], true);
        assert!(!output["diagnostics"].as_array().unwrap().is_empty());
        assert!(output.get("graph").is_none());
    }

    #[test]
    fn admission_failure_is_forwarded_without_structural_validation() {
        let output = inspect_source(br#"{}"#);
        let value: Value = provisional_json::from_str(&output.json).unwrap();
        assert_eq!(output.exit_code, 1);
        assert_eq!(value["status"], "invalid-source");
        assert_eq!(value["stage"], "admission");
        assert!(!value["diagnostics"].as_array().unwrap().is_empty());
    }

    struct RepeatingReader {
        remaining: usize,
    }

    impl std::io::Read for RepeatingReader {
        fn read(&mut self, buffer: &mut [u8]) -> std::io::Result<usize> {
            let amount = self.remaining.min(buffer.len());
            buffer[..amount].fill(b' ');
            self.remaining -= amount;
            Ok(amount)
        }
    }

    #[test]
    fn oversized_input_is_bounded_before_admission_resource_failure() {
        let mut reader = RepeatingReader {
            remaining: creature_kernel_core::body_document::ORDINARY_MAX_SOURCE_BYTES + 5,
        };
        let source = read_bounded(&mut reader).unwrap();
        assert_eq!(
            source.len(),
            creature_kernel_core::body_document::ORDINARY_MAX_SOURCE_BYTES + 1
        );
        assert_eq!(reader.remaining, 4);

        let output = inspect_source(&source);
        let value: Value = provisional_json::from_str(&output.json).unwrap();
        assert_eq!(output.exit_code, 1);
        assert_eq!(value["stage"], "admission");
        assert_eq!(value["status"], "resource-limit");
    }

    #[test]
    fn collection_permutation_has_identical_output() {
        let first = inspect(&format!("[{},{}]", root("root"), child("child", "root"))).0;
        let second = inspect(&format!("[{},{}]", child("child", "root"), root("root"))).0;
        assert_eq!(first, second);
        let roles: Vec<_> = first["graph"]["parts"]
            .as_array()
            .unwrap()
            .iter()
            .map(|part| part["address"]["role"].as_str().unwrap())
            .collect();
        assert_eq!(roles, ["child", "root"]);
    }

    #[test]
    fn output_is_one_object_with_stable_envelope_fields() {
        let output = inspect_source(&source("[]"));
        assert!(!output.json.ends_with('\n'));
        let value: Value = provisional_json::from_str(&output.json).unwrap();
        assert!(value.is_object());
        assert_eq!(value["format"], FORMAT);
        assert_eq!(value["operation"], "inspect-structure");
        for field in ["status", "stage", "diagnostics"] {
            assert!(value.get(field).is_some(), "missing {field}");
        }
    }

    #[test]
    fn help_forms_are_structured_success_responses() {
        for (arguments, operation) in [
            (vec!["--help"], "help"),
            (vec!["inspect-structure", "--help"], "inspect-structure"),
        ] {
            let output = run_cli(arguments);
            assert_eq!(output.exit_code, 0);
            assert!(!output.json.ends_with('\n'));
            let value: Value = provisional_json::from_str(&output.json).unwrap();
            assert!(value.is_object());
            assert_eq!(value["operation"], operation);
            assert_eq!(value["status"], "success");
            assert_eq!(value["processing_complete"], true);
            assert_eq!(value["diagnostics_complete"], true);
            assert!(value["help"].is_object());
            assert!(value["diagnostics"].as_array().unwrap().is_empty());
            let stdout = format!("{}\n", output.json);
            assert_eq!(stdout.matches('\n').count(), 1);
            assert!(provisional_json::from_str::<Value>(&stdout).is_ok());
        }
    }

    #[test]
    fn top_level_help_advertises_both_inspection_commands() {
        let output = run_cli(["--help"]);
        let value: Value = provisional_json::from_str(&output.json).unwrap();
        let commands = value["help"]["commands"].as_array().unwrap();
        let names: Vec<_> = commands
            .iter()
            .map(|command| command["command"].as_str().unwrap())
            .collect();
        assert_eq!(
            names,
            vec![
                "inspect-structure",
                "inspect-prepared-source",
                "inspect-provisional-form"
            ]
        );

        let command_help = run_cli(["inspect-structure", "--help"]);
        let command_help: Value = provisional_json::from_str(&command_help.json).unwrap();
        assert!(command_help["help"].get("commands").is_none());
    }

    #[test]
    fn usage_and_input_failures_are_json_only_outcomes() {
        let usage = run_cli(["inspect-structure"]);
        assert_eq!(usage.exit_code, 1);
        let usage_value: Value = provisional_json::from_str(&usage.json).unwrap();
        assert!(usage_value.is_object());
        assert_eq!(usage_value["processing_complete"], false);
        assert_eq!(usage_value["diagnostics_complete"], true);

        let input = run_cli([
            "inspect-structure",
            "--input",
            "/definitely/not/a/body.json",
        ]);
        assert_eq!(input.exit_code, 1);
        let value: Value = provisional_json::from_str(&input.json).unwrap();
        assert_eq!(value["status"], "input-failure");
        assert_eq!(value["processing_complete"], false);
        assert_eq!(value["diagnostics_complete"], true);
    }

    #[test]
    fn nested_unordered_collections_have_identical_output_when_permuted() {
        let parts = format!("[{},{}]", root("root"), child("child", "root"));
        let reversed_parts = format!("[{},{}]", child("child", "root"), root("root"));
        let dependencies = format!(
            "[{},{}]",
            dependency("zeta", "zeta_doc", '1'),
            dependency("alpha", "alpha_doc", '2')
        );
        let reversed_dependencies = format!(
            "[{},{}]",
            dependency("alpha", "alpha_doc", '2'),
            dependency("zeta", "zeta_doc", '1')
        );
        let extensions = format!(
            "[{},{}]",
            extension("zeta", 2, r#"{"z":2,"a":1}"#),
            extension("alpha", 1, r#"{"b":2,"a":1}"#)
        );
        let reversed_extensions = format!(
            "[{},{}]",
            extension("alpha", 1, r#"{"b":2,"a":1}"#),
            extension("zeta", 2, r#"{"z":2,"a":1}"#)
        );
        let regions = format!(
            "[{},{}]",
            region(
                "region_b",
                &format!("[{},{}]", part_reference("child"), part_reference("root"))
            ),
            region("region_a", &format!("[{}]", part_reference("root")))
        );
        let reversed_regions = format!(
            "[{},{}]",
            region("region_a", &format!("[{}]", part_reference("root"))),
            region(
                "region_b",
                &format!("[{},{}]", part_reference("root"), part_reference("child"))
            )
        );
        let capabilities = format!(
            "[{},{}]",
            capability(
                "capability_b",
                &format!("[{},{}]", part_reference("child"), part_reference("root"))
            ),
            capability("capability_a", &format!("[{}]", part_reference("root")))
        );
        let reversed_capabilities = format!(
            "[{},{}]",
            capability("capability_a", &format!("[{}]", part_reference("root"))),
            capability(
                "capability_b",
                &format!("[{},{}]", part_reference("root"), part_reference("child"))
            )
        );

        let first = inspect_source(&source_with(
            &parts,
            &dependencies,
            &extensions,
            &regions,
            &capabilities,
        ));
        let second = inspect_source(&source_with(
            &reversed_parts,
            &reversed_dependencies,
            &reversed_extensions,
            &reversed_regions,
            &reversed_capabilities,
        ));
        assert_eq!(first.exit_code, 0);
        assert_eq!(second.exit_code, 0);
        assert_eq!(first.json, second.json);
    }
}
