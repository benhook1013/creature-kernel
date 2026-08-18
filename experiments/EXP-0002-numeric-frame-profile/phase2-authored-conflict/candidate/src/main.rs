//! Standalone, non-authoritative JSONL observer for the EXP-0002 successor.
//!
//! This executable is deliberately only a bounded transport adapter around
//! `provisional_authored_conflict_candidate`.  It does not select a profile,
//! resolve a source set, create a snapshot, or produce experiment evidence.

use std::collections::HashSet;
use std::fmt;
use std::io::{self, BufRead, BufReader, Write};

use creature_kernel_core::body_document::ResourceProfile;
use creature_kernel_core::provisional_authored_conflict_candidate as bridge;
use creature_kernel_core::provisional_authored_conflict_candidate::{
    ProvisionalAttachmentComparison, ProvisionalAttachmentOutcome,
    ProvisionalAuthoredConflictTolerances, ProvisionalComparisonComponent,
    ProvisionalMemberOutcome, ProvisionalProviderPhase,
};
use creature_kernel_core::provisional_json as json;
use creature_kernel_core::quaternion_normalization::{
    Binary64ArithmeticProvider, Binary64ArithmeticProviderFailure, CorrectlyRoundedSqrt,
    GateRejection, QuaternionNormalizationGate, SqrtProviderFailure,
};
use serde::de::{self, DeserializeSeed, MapAccess, SeqAccess, Visitor};
use serde::{Deserializer, Serialize};

const REQUEST_PROTOCOL_ID: &str = "ck.exp-0002.r3-authored-conflict-candidate-request-1";
const RESPONSE_PROTOCOL_ID: &str = "ck.exp-0002.r3-authored-conflict-candidate-response-1";
const OPERATION: &str = "observe-authored-conflict";
const RESOURCE_PROFILE: &str = "ordinary";
const ENVIRONMENT: &str = "unattested-no-probe-v1";
const MAX_FRAME_BYTES: usize = 64 * 1024;
const MAX_SOURCE_BYTES: usize = 24 * 1024;
const MAX_REQUEST_ID_BYTES: usize = 256;

enum InputFrame {
    End,
    Record(Vec<u8>),
    Oversized,
}

#[derive(Clone, Debug)]
struct Request {
    protocol_id: String,
    request_id: String,
    operation: String,
    resource_profile: String,
    source: String,
    translation_absolute: json::Value,
    translation_relative: json::Value,
    rotation_half_chord: json::Value,
    gate: String,
    arithmetic: String,
    sqrt: String,
    environment: String,
}

#[derive(Debug, Serialize)]
struct Response {
    protocol_id: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    request_id: Option<String>,
    status: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    observations: Option<json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    detail: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    cause: Option<json::Value>,
}

fn main() -> io::Result<()> {
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut input = BufReader::new(stdin.lock());
    let mut output = io::BufWriter::new(stdout.lock());

    loop {
        let response = match read_input_frame(&mut input)? {
            InputFrame::End => break,
            InputFrame::Oversized => resource_response(None, "request-line-bytes"),
            InputFrame::Record(bytes) => process_record(&bytes),
        };
        write_response(&mut output, response)?;
    }
    Ok(())
}

fn process_record(bytes: &[u8]) -> Response {
    let line = match std::str::from_utf8(bytes) {
        Ok(line) => line,
        Err(_) => return error_response(None, "malformed-request", None),
    };
    if line.trim().is_empty() {
        return error_response(None, "malformed-request", None);
    }
    match parse_request(line) {
        Ok(request) => dispatch_request(request),
        Err(request_id) => error_response(request_id, "malformed-request", None),
    }
}

/// Read exactly one LF-delimited record while retaining the 64 KiB wire cap.
/// A final record at EOF is accepted when it is within the same cap.
fn read_input_frame(reader: &mut impl BufRead) -> io::Result<InputFrame> {
    let mut frame = Vec::with_capacity(MAX_FRAME_BYTES);
    loop {
        let available = reader.fill_buf()?;
        if available.is_empty() {
            return if frame.is_empty() {
                Ok(InputFrame::End)
            } else {
                Ok(InputFrame::Record(frame))
            };
        }

        let newline = available.iter().position(|byte| *byte == b'\n');
        let take = newline.map_or(available.len(), |index| index + 1);
        if frame.len().saturating_add(take) > MAX_FRAME_BYTES {
            reader.consume(take);
            if newline.is_none() {
                drain_input_record(reader)?;
            }
            return Ok(InputFrame::Oversized);
        }

        frame.extend_from_slice(&available[..take]);
        reader.consume(take);
        if newline.is_some() {
            return Ok(InputFrame::Record(frame));
        }
    }
}

fn drain_input_record(reader: &mut impl BufRead) -> io::Result<()> {
    loop {
        let available = reader.fill_buf()?;
        if available.is_empty() {
            return Ok(());
        }
        let take = available
            .iter()
            .position(|byte| *byte == b'\n')
            .map_or(available.len(), |index| index + 1);
        let has_newline = available[..take].contains(&b'\n');
        reader.consume(take);
        if has_newline {
            return Ok(());
        }
    }
}

/// Parse with a recursive duplicate-member check, then manually enforce the
/// closed request shape.  The source is retained as the decoded JSON string;
/// no JSON parse/reserialize round-trip is performed on it.
fn parse_request(line: &str) -> Result<Request, Option<String>> {
    let request_id_hint = request_id_hint(line);
    if reject_duplicate_members(line).is_err() {
        return Err(request_id_hint);
    }
    let value: json::Value = json::from_str(line).map_err(|_| request_id_hint.clone())?;
    let map = value.as_object().ok_or(request_id_hint.clone())?;
    if !exact_keys(
        map,
        &[
            "protocol_id",
            "request_id",
            "operation",
            "resource_profile",
            "source",
            "tolerances",
            "providers",
        ],
    ) {
        return Err(request_id_hint);
    }

    let protocol_id = required_string(map, "protocol_id").ok_or(request_id_hint.clone())?;
    let request_id = required_string(map, "request_id").ok_or(request_id_hint.clone())?;
    let operation = required_string(map, "operation").ok_or(request_id_hint.clone())?;
    let resource_profile =
        required_string(map, "resource_profile").ok_or(request_id_hint.clone())?;
    let source = required_string(map, "source").ok_or(request_id_hint.clone())?;

    let tolerances = map
        .get("tolerances")
        .and_then(json::Value::as_object)
        .ok_or(request_id_hint.clone())?;
    if !exact_keys(
        tolerances,
        &[
            "translation_absolute",
            "translation_relative",
            "rotation_half_chord",
        ],
    ) {
        return Err(request_id_hint);
    }
    let translation_absolute = tolerances
        .get("translation_absolute")
        .cloned()
        .ok_or(request_id_hint.clone())?;
    let translation_relative = tolerances
        .get("translation_relative")
        .cloned()
        .ok_or(request_id_hint.clone())?;
    let rotation_half_chord = tolerances
        .get("rotation_half_chord")
        .cloned()
        .ok_or(request_id_hint.clone())?;

    let providers = map
        .get("providers")
        .and_then(json::Value::as_object)
        .ok_or(request_id_hint.clone())?;
    if !exact_keys(providers, &["gate", "arithmetic", "sqrt", "environment"]) {
        return Err(request_id_hint);
    }
    let gate = required_string(providers, "gate").ok_or(request_id_hint.clone())?;
    let arithmetic = required_string(providers, "arithmetic").ok_or(request_id_hint.clone())?;
    let sqrt = required_string(providers, "sqrt").ok_or(request_id_hint.clone())?;
    let environment = required_string(providers, "environment").ok_or(request_id_hint.clone())?;

    Ok(Request {
        protocol_id,
        request_id,
        operation,
        resource_profile,
        source,
        translation_absolute,
        translation_relative,
        rotation_half_chord,
        gate,
        arithmetic,
        sqrt,
        environment,
    })
}

fn request_id_hint(line: &str) -> Option<String> {
    let value: json::Value = json::from_str(line).ok()?;
    let id = value.as_object()?.get("request_id")?.as_str()?.to_owned();
    valid_request_id(&id).then_some(id)
}

fn valid_request_id(value: &str) -> bool {
    !value.is_empty() && value.as_bytes().len() <= MAX_REQUEST_ID_BYTES
}

fn exact_keys(map: &json::Map<String, json::Value>, expected: &[&str]) -> bool {
    map.len() == expected.len() && expected.iter().all(|key| map.contains_key(*key))
}

fn required_string(map: &json::Map<String, json::Value>, key: &str) -> Option<String> {
    map.get(key)
        .and_then(json::Value::as_str)
        .map(str::to_owned)
}

fn reject_duplicate_members(input: &str) -> Result<(), ()> {
    let mut deserializer = json::Deserializer::from_str(input);
    deserializer
        .deserialize_any(DuplicateKeyVisitor)
        .map_err(|_| ())?;
    deserializer.end().map_err(|_| ())
}

struct DuplicateKeyVisitor;
struct DuplicateValueSeed;

impl<'de> DeserializeSeed<'de> for DuplicateValueSeed {
    type Value = ();

    fn deserialize<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(DuplicateKeyVisitor)
    }
}

impl<'de> Visitor<'de> for DuplicateKeyVisitor {
    type Value = ();

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("a JSON value without duplicate object members")
    }

    fn visit_bool<E>(self, _value: bool) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(())
    }

    fn visit_i64<E>(self, _value: i64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(())
    }

    fn visit_u64<E>(self, _value: u64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(())
    }

    fn visit_f64<E>(self, _value: f64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(())
    }

    fn visit_str<E>(self, _value: &str) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(())
    }

    fn visit_borrowed_str<E>(self, _value: &'de str) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(())
    }

    fn visit_unit<E>(self) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Ok(())
    }

    fn visit_seq<A>(self, mut sequence: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        while sequence.next_element_seed(DuplicateValueSeed)?.is_some() {}
        Ok(())
    }

    fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut keys = HashSet::new();
        while let Some(key) = map.next_key::<String>()? {
            if !keys.insert(key) {
                return Err(de::Error::custom("duplicate JSON object member"));
            }
            map.next_value_seed(DuplicateValueSeed)?;
        }
        Ok(())
    }
}

fn dispatch_request(request: Request) -> Response {
    if request.protocol_id != REQUEST_PROTOCOL_ID || !valid_request_id(&request.request_id) {
        let id = valid_request_id(&request.request_id).then_some(request.request_id);
        return error_response(id, "malformed-request", None);
    }
    if request.operation != OPERATION {
        return unsupported_response(request.request_id, "unsupported-operation", None);
    }
    if request.resource_profile != RESOURCE_PROFILE {
        return unsupported_response(
            request.request_id,
            "unsupported-resource-profile",
            Some("only ordinary is supported in this candidate slice"),
        );
    }
    if request.environment != ENVIRONMENT
        || !matches!(request.gate.as_str(), "allow" | "reject")
        || !matches!(request.arithmetic.as_str(), "native" | "unavailable")
        || !matches!(request.sqrt.as_str(), "native" | "unavailable")
    {
        return rejected_response(request.request_id, "provider-selection", None::<String>);
    }

    if request.source.as_bytes().len() > MAX_SOURCE_BYTES {
        return resource_response(Some(request.request_id), "source-bytes");
    }

    let translation_absolute = match admit_request_tolerance(
        &request.request_id,
        &request.translation_absolute,
        bridge::ProvisionalToleranceField::TranslationAbsolute,
    ) {
            Ok(value) => value,
            Err(response) => return response,
        };
    let translation_relative = match admit_request_tolerance(
        &request.request_id,
        &request.translation_relative,
        bridge::ProvisionalToleranceField::TranslationRelative,
    ) {
            Ok(value) => value,
            Err(response) => return response,
        };
    let rotation_half_chord = match admit_request_tolerance(
        &request.request_id,
        &request.rotation_half_chord,
        bridge::ProvisionalToleranceField::RotationHalfChord,
    ) {
            Ok(value) => value,
            Err(response) => return response,
        };

    let tolerances = ProvisionalAuthoredConflictTolerances {
        translation_absolute,
        translation_relative,
        rotation_half_chord,
    };
    let gate = request.gate == "allow";
    let arithmetic = request.arithmetic == "native";
    let sqrt = request.sqrt == "native";
    let result = bridge::observe_provisional_authored_conflict(
        request.source.as_bytes(),
        ResourceProfile::ORDINARY,
        tolerances,
        move |_phase: ProvisionalProviderPhase| ConfiguredGate { allow: gate },
        move |_phase: ProvisionalProviderPhase| {
            arithmetic.then(|| Box::new(NativeArithmetic) as Box<dyn Binary64ArithmeticProvider>)
        },
        move |_phase: ProvisionalProviderPhase| {
            sqrt.then(|| Box::new(NativeSqrt) as Box<dyn CorrectlyRoundedSqrt>)
        },
    );
    let request_id = request.request_id.clone();
    match result {
        Ok(observation) => observed_response(
            request_id,
            observation_value(observation, &request, tolerances),
        ),
        Err(error) => {
            let cause = match &error {
                bridge::ProvisionalAuthoredConflictError::InvalidTolerance(error) => {
                    let cause = error.numeric_cause();
                    Some(cause_value(cause.code(), &cause))
                }
                _ => None,
            };
            rejected_response_with_cause(request_id, error.code(), Some(error.to_string()), cause)
        }
    }
}

/// JSON numbers are retained by serde_json's arbitrary-precision feature.
/// Parsing the lexical number to f64 only at this boundary lets exponent
/// overflow reach the bridge as infinity, where it is rejected explicitly.
const INVALID_TOLERANCE_CODE: &str = "ck.provisional-r3-authored-conflict.invalid-tolerance";

enum ToleranceNumberError {
    Malformed,
    NonzeroUnderflow { lexeme: String },
}

fn admit_request_tolerance(
    request_id: &str,
    value: &json::Value,
    field: bridge::ProvisionalToleranceField,
) -> Result<f64, Response> {
    match tolerance_number(value) {
        Ok(value) => Ok(value),
        Err(ToleranceNumberError::Malformed) => Err(error_response(
            Some(request_id.to_owned()),
            "malformed-request",
            None,
        )),
        Err(ToleranceNumberError::NonzeroUnderflow { lexeme }) => {
            let cause = bridge::ProvisionalNumericSkipCause::InvalidProfile {
                field,
                failure: bridge::ProvisionalInvalidProfileFailure::NonzeroUnderflow,
            };
            Err(rejected_response_with_cause(
                request_id.to_owned(),
                INVALID_TOLERANCE_CODE,
                Some(format!(
                    "nonzero decimal tolerance underflowed to binary64 zero: {lexeme}"
                )),
                Some(cause_value(cause.code(), &cause)),
            ))
        }
    }
}

fn tolerance_number(value: &json::Value) -> Result<f64, ToleranceNumberError> {
    let number = value.as_number().ok_or(ToleranceNumberError::Malformed)?;
    let lexeme = number.to_string();
    let value = match lexeme.parse::<f64>() {
        Ok(value) => value,
        Err(_) if lexeme.starts_with('-') => f64::NEG_INFINITY,
        Err(_) => f64::INFINITY,
    };
    if value == 0.0 {
        if coefficient_is_nonzero(&lexeme) {
            return Err(ToleranceNumberError::NonzeroUnderflow { lexeme });
        }
        return Ok(0.0);
    }
    Ok(value)
}

fn coefficient_is_nonzero(lexeme: &str) -> bool {
    let coefficient = lexeme
        .strip_prefix('-')
        .unwrap_or(lexeme)
        .split_once(['e', 'E'])
        .map_or(
            lexeme.strip_prefix('-').unwrap_or(lexeme),
            |(coefficient, _)| coefficient,
        );
    coefficient
        .bytes()
        .any(|byte| byte.is_ascii_digit() && byte != b'0')
}

struct ConfiguredGate {
    allow: bool,
}

impl QuaternionNormalizationGate for ConfiguredGate {
    fn validate_input(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
        self.allow.then_some(()).ok_or(GateRejection::Rejected)
    }

    fn validate_scaled_norm(&mut self, _squared_norm: f64) -> Result<(), GateRejection> {
        self.allow.then_some(()).ok_or(GateRejection::Rejected)
    }

    fn validate_output(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
        self.allow.then_some(()).ok_or(GateRejection::Rejected)
    }
}

struct NativeArithmetic;

impl Binary64ArithmeticProvider for NativeArithmetic {
    fn add(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure> {
        Ok(left + right)
    }

    fn sub(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure> {
        Ok(left - right)
    }

    fn mul(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure> {
        Ok(left * right)
    }

    fn div(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure> {
        Ok(left / right)
    }
}

struct NativeSqrt;

impl CorrectlyRoundedSqrt for NativeSqrt {
    fn sqrt(&mut self, input: f64) -> Result<f64, SqrtProviderFailure> {
        Ok(input.sqrt())
    }
}

fn observation_value(
    observation: bridge::ProvisionalAuthoredConflictObservation,
    request: &Request,
    tolerances: ProvisionalAuthoredConflictTolerances,
) -> json::Value {
    let members = observation
        .members
        .into_iter()
        .map(|member| match member.outcome {
            ProvisionalMemberOutcome::Compared(attachments) => json::json!({
                "identity": identity_value(member.identity),
                "role": role_name(member.role),
                "outcome": "compared",
                "attachments": attachments.into_iter().map(attachment_value).collect::<Vec<_>>(),
            }),
            ProvisionalMemberOutcome::Skipped(skip) => {
                let cause = cause_value(skip.cause.code(), &skip.cause);
                json::json!({
                    "identity": identity_value(member.identity),
                    "role": role_name(member.role),
                    "outcome": "skipped",
                    "attachments": [],
                    "skip": {"code": skip.code, "detail": skip.detail, "cause": cause},
                })
            }
        })
        .collect::<Vec<_>>();
    json::json!({
        "root": identity_value(observation.root),
        "members": members,
        "tolerances": {
            "translation_absolute": f64_bits(tolerances.translation_absolute),
            "translation_relative": f64_bits(tolerances.translation_relative),
            "rotation_half_chord": f64_bits(tolerances.rotation_half_chord),
        },
        "providers": {
            "gate": {"selection": request.gate, "attestation": "unattested"},
            "arithmetic": {"selection": request.arithmetic, "attestation": "unattested"},
            "sqrt": {"selection": request.sqrt, "attestation": "unattested"},
            "environment": ENVIRONMENT,
        },
        "detail": "provisional bridge observation; equation and typed cause evidence retained",
    })
}

fn f64_bits(value: f64) -> json::Value {
    json::Value::String(format!("0x{:016x}", value.to_bits()))
}

fn identity_value(identity: bridge::ProvisionalMemberIdentity) -> json::Value {
    json::json!({"document": identity.document, "namespace": identity.namespace})
}

fn role_name(role: bridge::ProvisionalMemberRole) -> &'static str {
    match role {
        bridge::ProvisionalMemberRole::Root => "root",
        bridge::ProvisionalMemberRole::Dependency => "dependency",
    }
}

fn address_value(address: bridge::ProvisionalSemanticAddress) -> json::Value {
    json::json!({
        "namespace": address.namespace,
        "anchors": address.anchors,
        "kind": address.kind,
        "role": address.role,
    })
}

fn transform_value(transform: bridge::ProvisionalRigidTransform) -> json::Value {
    json::json!({
        "translation": transform.translation.map(bits_string),
        "rotation_xyzw": transform.rotation_xyzw.map(bits_string),
    })
}

fn bits_string(value: creature_kernel_core::numeric::NormalizedBinary64) -> String {
    format!("0x{:016x}", value.to_bits())
}

fn attachment_value(attachment: ProvisionalAttachmentComparison) -> json::Value {
    let mut value = json::json!({
        "provenance": {
            "attachment": address_value(attachment.provenance.attachment),
            "root": address_value(attachment.provenance.root),
            "host_socket": address_value(attachment.provenance.host_socket),
            "mating_socket": address_value(attachment.provenance.mating_socket),
            "host_owner": address_value(attachment.provenance.host_owner),
            "mating_owner": address_value(attachment.provenance.mating_owner),
            "offset": transform_value(attachment.provenance.offset),
            "root_to_mating_owner_path": attachment.provenance.root_to_mating_owner_path
                .into_iter().map(address_value).collect::<Vec<_>>(),
        },
        "equation": {
            "host_socket_local": transform_value(attachment.provenance.host_socket_local),
            "mating_socket_local": transform_value(attachment.provenance.mating_socket_local),
            "root_to_mating_owner_part_locals": attachment.provenance.root_to_mating_owner_part_locals
                .into_iter()
                .map(|part| json::json!({
                    "address": address_value(part.address),
                    "local": transform_value(part.local),
                }))
                .collect::<Vec<_>>(),
            "equation_steps": attachment.provenance.equation_steps
                .into_iter()
                .map(|step| json::json!({
                    "operation": placement_operation_name(step.operation),
                    "output": transform_value(step.output),
                }))
                .collect::<Vec<_>>(),
        },
        "authored_root_local": transform_value(attachment.authored_root_local),
        "derived_root_local": transform_value(attachment.derived_root_local),
    });
    let object = value.as_object_mut().expect("object literal");
    match attachment.outcome {
        ProvisionalAttachmentOutcome::Agree => {
            object.insert(
                "outcome".to_owned(),
                json::Value::String("agree".to_owned()),
            );
        }
        ProvisionalAttachmentOutcome::Conflict => {
            object.insert(
                "outcome".to_owned(),
                json::Value::String("conflict".to_owned()),
            );
        }
        ProvisionalAttachmentOutcome::Skipped(skip) => {
            let mut cause = cause_value(skip.cause.code(), &skip.cause);
            cause
                .as_object_mut()
                .expect("serialized numeric cause object")
                .insert(
                    "component".to_owned(),
                    json::Value::String(component_name(skip.component).to_owned()),
                );
            object.insert(
                "outcome".to_owned(),
                json::Value::String("skipped".to_owned()),
            );
            object.insert(
                "component".to_owned(),
                json::Value::String(component_name(skip.component).to_owned()),
            );
            object.insert("code".to_owned(), json::Value::String(skip.code.to_owned()));
            object.insert("detail".to_owned(), json::Value::String(skip.detail));
            object.insert("cause".to_owned(), cause);
        }
    }
    value
}

/// Serialize an owned tagged cause, inject its full family code, and expose
/// the leaf failure with its typed context as compact sibling fields.
fn cause_value<T: Serialize>(code: &'static str, cause: &T) -> json::Value {
    let mut value = json::to_value(cause).expect("owned cause vocabulary serializes");
    let object = value
        .as_object_mut()
        .expect("owned cause vocabulary is a tagged object");
    let variant = object.remove("kind");
    match object.get("failure") {
        Some(json::Value::String(_)) => {}
        Some(json::Value::Object(_)) => {
            let nested = object.remove("failure").expect("nested failure");
            let mut nested = nested.as_object().expect("tagged failure object").clone();
            let mut leaf = nested.remove("kind");
            if let Some(context) = nested.remove("context") {
                let mut context = context
                    .as_object()
                    .expect("tagged failure context object")
                    .clone();
                leaf = context.remove("kind").or(leaf);
                object.extend(context);
            }
            object.insert("failure".to_owned(), leaf.expect("stable failure tag"));
        }
        None => {
            object.insert("failure".to_owned(), variant.expect("stable cause tag"));
        }
        Some(_) => panic!("owned cause failure has an unexpected shape"),
    }
    object.insert("code".to_owned(), json::Value::String(code.to_owned()));
    value
}

fn placement_operation_name(operation: bridge::ProvisionalPlacementOperation) -> &'static str {
    match operation {
        bridge::ProvisionalPlacementOperation::PartContainment => "part-containment",
        bridge::ProvisionalPlacementOperation::AttachmentContainment => "attachment-containment",
        bridge::ProvisionalPlacementOperation::AttachmentMatingSocket => "attachment-mating-socket",
        bridge::ProvisionalPlacementOperation::AttachmentHostOffset => "attachment-host-offset",
        bridge::ProvisionalPlacementOperation::AttachmentInverse => "attachment-inverse",
        bridge::ProvisionalPlacementOperation::AttachmentEquation => "attachment-equation",
    }
}

fn component_name(component: ProvisionalComparisonComponent) -> &'static str {
    match component {
        ProvisionalComparisonComponent::Translation => "translation",
        ProvisionalComparisonComponent::Rotation => "rotation",
    }
}

fn observed_response(request_id: String, observations: json::Value) -> Response {
    Response {
        protocol_id: RESPONSE_PROTOCOL_ID,
        request_id: Some(request_id),
        status: "observed",
        observations: Some(observations),
        error: None,
        detail: None,
        cause: None,
    }
}

fn rejected_response(request_id: String, error: &str, detail: Option<String>) -> Response {
    Response {
        protocol_id: RESPONSE_PROTOCOL_ID,
        request_id: Some(request_id),
        status: "rejected",
        observations: None,
        error: Some(error.to_owned()),
        detail,
        cause: None,
    }
}

fn rejected_response_with_cause(
    request_id: String,
    error: &str,
    detail: Option<String>,
    cause: Option<json::Value>,
) -> Response {
    let mut response = rejected_response(request_id, error, detail);
    response.cause = cause;
    response
}

fn unsupported_response(request_id: String, error: &str, detail: Option<&str>) -> Response {
    Response {
        protocol_id: RESPONSE_PROTOCOL_ID,
        request_id: Some(request_id),
        status: "unsupported",
        observations: None,
        error: Some(error.to_owned()),
        detail: detail.map(str::to_owned),
        cause: None,
    }
}

fn error_response(request_id: Option<String>, error: &str, detail: Option<&str>) -> Response {
    Response {
        protocol_id: RESPONSE_PROTOCOL_ID,
        request_id,
        status: "error",
        observations: None,
        error: Some(error.to_owned()),
        detail: detail.map(str::to_owned),
        cause: None,
    }
}

fn resource_response(request_id: Option<String>, error: &str) -> Response {
    Response {
        protocol_id: RESPONSE_PROTOCOL_ID,
        request_id,
        status: "resource-limit",
        observations: None,
        error: Some(error.to_owned()),
        detail: None,
        cause: None,
    }
}

fn write_response(output: &mut impl Write, response: Response) -> io::Result<()> {
    let request_id = response.request_id.clone();
    let serialized = json::to_string(&response)
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?;
    let serialized = if serialized.len().saturating_add(1) <= MAX_FRAME_BYTES {
        serialized
    } else {
        let fallback = resource_response(request_id, "response-line-bytes");
        json::to_string(&fallback)
            .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?
    };
    writeln!(output, "{serialized}")?;
    output.flush()
}

#[cfg(test)]
mod tests {
    use super::*;

    const SOURCE: &str =
        include_str!("../../../../../examples/body-documents/stylized-digitigrade-biped.json");

    fn request_value(source: &str) -> json::Value {
        json::json!({
            "protocol_id": REQUEST_PROTOCOL_ID,
            "request_id": "test-1",
            "operation": OPERATION,
            "resource_profile": RESOURCE_PROFILE,
            "source": source,
            "tolerances": {"translation_absolute": 0.0, "translation_relative": 0.0, "rotation_half_chord": 0.0},
            "providers": {"gate": "allow", "arithmetic": "native", "sqrt": "native", "environment": ENVIRONMENT}
        })
    }

    fn request(source: &str) -> Request {
        parse_request(&json::to_string(&request_value(source)).unwrap()).unwrap()
    }

    fn response(source: &str) -> Response {
        dispatch_request(request(source))
    }

    fn socket_transform(z: &str) -> json::Value {
        json::json!({
            "translation": ["0x0000000000000000", "0x0000000000000000", z],
            "rotation_xyzw": [
                "0x0000000000000000",
                "0x0000000000000000",
                "0x0000000000000000",
                "0x3ff0000000000000"
            ]
        })
    }

    #[test]
    fn exact_example_is_one_root_attachment_and_agree() {
        let response = response(SOURCE);
        assert_eq!(response.status, "observed");
        let members = response.observations.unwrap()["members"]
            .as_array()
            .unwrap()
            .to_owned();
        assert_eq!(members.len(), 1);
        assert_eq!(members[0]["role"], "root");
        assert_eq!(members[0]["outcome"], "compared");
        assert_eq!(members[0]["attachments"].as_array().unwrap().len(), 1);
        assert_eq!(members[0]["attachments"][0]["outcome"], "agree");
        let attachment = &members[0]["attachments"][0];
        let equation = &attachment["equation"];
        assert_eq!(
            equation["host_socket_local"],
            socket_transform("0xbff0000000000000")
        );
        assert_eq!(
            equation["mating_socket_local"],
            socket_transform("0x0000000000000000")
        );
        assert!(
            equation["root_to_mating_owner_part_locals"]
                .as_array()
                .unwrap()
                .is_empty()
        );
        let operations = equation["equation_steps"]
            .as_array()
            .unwrap()
            .iter()
            .map(|step| step["operation"].as_str().unwrap())
            .collect::<Vec<_>>();
        assert_eq!(
            operations,
            vec![
                "attachment-host-offset",
                "attachment-inverse",
                "attachment-equation"
            ]
        );
        assert_eq!(
            equation["equation_steps"]
                .as_array()
                .unwrap()
                .last()
                .unwrap()["output"],
            attachment["derived_root_local"]
        );
        assert_eq!(
            members[0]["attachments"][0]["authored_root_local"]["translation"][0],
            "0x0000000000000000"
        );
    }

    #[test]
    fn authored_translation_conflicts_at_zero_and_agrees_at_explicit_one() {
        let modified = SOURCE.replace(
            r#""placement": {"translation": [0, 0, -1], "rotation_xyzw": [0, 0, 0, 1]}"#,
            r#""placement": {"translation": [1, 0, -1], "rotation_xyzw": [0, 0, 0, 1]}"#,
        );
        let zero = response(&modified);
        assert_eq!(
            zero.observations.unwrap()["members"][0]["attachments"][0]["outcome"],
            "conflict"
        );
        let mut one = request(&modified);
        one.translation_absolute = json::json!(1.0);
        let at_one = dispatch_request(one);
        assert_eq!(
            at_one.observations.unwrap()["members"][0]["attachments"][0]["outcome"],
            "agree"
        );
    }

    #[test]
    fn negative_and_overflow_tolerances_are_rejected_and_never_defaulted() {
        let mut negative = request(SOURCE);
        negative.translation_relative = json::json!(-1.0);
        let result = dispatch_request(negative);
        assert_eq!(result.status, "rejected");
        assert_eq!(
            result.error.as_deref(),
            Some("ck.provisional-r3-authored-conflict.invalid-tolerance")
        );
        let cause = result.cause.as_ref().expect("typed tolerance cause");
        assert_eq!(
            cause["code"],
            "ck.provisional-r3-authored-conflict.numeric-comparison.invalid-profile"
        );
        assert_eq!(cause["field"], "translation-relative");
        assert_eq!(cause["failure"], "negative");

        let mut overflow = request(SOURCE);
        overflow.rotation_half_chord = json::from_str("1e9999").unwrap();
        let result = dispatch_request(overflow);
        assert_eq!(result.status, "rejected");
        assert_eq!(
            result.error.as_deref(),
            Some("ck.provisional-r3-authored-conflict.invalid-tolerance")
        );
    }

    #[test]
    fn decimal_underflow_zero_coefficient_and_signed_zero_are_explicit() {
        let mut underflow = request(SOURCE);
        underflow.translation_absolute = json::from_str("1e-9999").unwrap();
        let result = dispatch_request(underflow);
        assert_eq!(result.status, "rejected");
        assert_eq!(result.error.as_deref(), Some(INVALID_TOLERANCE_CODE));
        assert!(result.detail.unwrap().contains("1e-9999"));

        let mut zero_coefficient = request(SOURCE);
        zero_coefficient.translation_absolute = json::from_str("0e-9999").unwrap();
        let result = dispatch_request(zero_coefficient);
        assert_eq!(result.status, "observed");
        assert_eq!(
            result.observations.unwrap()["tolerances"]["translation_absolute"],
            "0x0000000000000000"
        );

        let mut signed_zero = request(SOURCE);
        signed_zero.translation_absolute = json::json!(-0.0);
        let result = dispatch_request(signed_zero);
        assert_eq!(result.status, "observed");
        assert_eq!(
            result.observations.unwrap()["tolerances"]["translation_absolute"],
            "0x0000000000000000"
        );
    }

    #[test]
    fn declared_dependency_is_rejected() {
        let modified = SOURCE.replace(
            r#""dependencies": []"#,
            r#""dependencies": [{"document":"dep","namespace":"dep","content_sha256":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}]"#,
        );
        let result = response(&modified);
        assert_eq!(result.status, "rejected");
        assert_eq!(
            result.error.as_deref(),
            Some("ck.provisional-r3-authored-conflict.declared-dependency")
        );
    }

    #[test]
    fn unavailable_provider_and_reject_gate_are_member_skips() {
        let mut unavailable = request(SOURCE);
        unavailable.arithmetic = "unavailable".to_owned();
        let result = dispatch_request(unavailable);
        assert_eq!(result.status, "observed");
        assert_eq!(
            result.observations.as_ref().unwrap()["members"][0]["outcome"],
            "skipped"
        );
        let cause = &result.observations.as_ref().unwrap()["members"][0]["skip"]["cause"];
        assert_eq!(
            cause["code"],
            "ck.provisional-r3-authored-conflict.frame-value.quaternion"
        );
        assert_eq!(cause["failure"], "provider-unavailable");
        assert_eq!(cause["operation"], "div");
        assert_eq!(cause["stage"], "scaled-component");
        assert_eq!(cause["index"], 0);
        let mut rejected = request(SOURCE);
        rejected.gate = "reject".to_owned();
        let result = dispatch_request(rejected);
        assert_eq!(result.status, "observed");
        assert_eq!(
            result.observations.as_ref().unwrap()["members"][0]["outcome"],
            "skipped"
        );
        let cause = &result.observations.as_ref().unwrap()["members"][0]["skip"]["cause"];
        assert_eq!(cause["failure"], "gate-rejected");
        assert_eq!(cause["stage"], "input");
    }

    #[test]
    fn malformed_record_recovers_to_valid_record() {
        let invalid = b"{\"request_id\":\"bad\"}\n";
        let valid = format!("{}\n", json::to_string(&request_value(SOURCE)).unwrap());
        let input_bytes = [invalid, valid.as_bytes()].concat();
        let mut input = BufReader::new(input_bytes.as_slice());
        let first_bytes = match read_input_frame(&mut input).unwrap() {
            InputFrame::Record(bytes) => bytes,
            _ => panic!("record"),
        };
        let first = process_record(&first_bytes);
        assert_eq!(first.status, "error");
        let second = match read_input_frame(&mut input).unwrap() {
            InputFrame::Record(bytes) => process_record(&bytes),
            _ => panic!("record"),
        };
        assert_eq!(second.status, "observed");
    }

    #[test]
    fn oversized_record_recovers_to_valid_record() {
        let valid = format!("{}\n", json::to_string(&request_value(SOURCE)).unwrap());
        let mut bytes = vec![b'x'; MAX_FRAME_BYTES + 1];
        bytes.push(b'\n');
        bytes.extend_from_slice(valid.as_bytes());
        let mut input = BufReader::new(bytes.as_slice());
        let first = read_input_frame(&mut input).unwrap();
        assert!(matches!(first, InputFrame::Oversized));
        let second = match read_input_frame(&mut input).unwrap() {
            InputFrame::Record(record) => process_record(&record),
            _ => panic!("record"),
        };
        assert_eq!(second.status, "observed");
    }

    #[test]
    fn source_and_request_bounds_and_response_fallback_are_bounded() {
        let mut too_long_id = request(SOURCE);
        too_long_id.request_id = "x".repeat(MAX_REQUEST_ID_BYTES + 1);
        let result = dispatch_request(too_long_id);
        assert_eq!(result.status, "error");
        assert!(result.request_id.is_none());
        let mut too_long_source = request(SOURCE);
        too_long_source.source = "x".repeat(MAX_SOURCE_BYTES + 1);
        let result = dispatch_request(too_long_source);
        assert_eq!(result.status, "resource-limit");
        assert_eq!(result.error.as_deref(), Some("source-bytes"));
        let response = observed_response(
            "id".to_owned(),
            json::json!({"x": "x".repeat(MAX_FRAME_BYTES)}),
        );
        let mut output = Vec::new();
        write_response(&mut output, response).unwrap();
        assert!(output.len() <= MAX_FRAME_BYTES);
        assert!(
            std::str::from_utf8(&output)
                .unwrap()
                .contains("response-line-bytes")
        );
    }

    #[test]
    fn multibyte_request_id_over_byte_bound_is_rejected_without_echo() {
        let mut value = request_value(SOURCE);
        let request_id = "é".repeat((MAX_REQUEST_ID_BYTES / "é".len()) + 1);
        assert!(request_id.len() > MAX_REQUEST_ID_BYTES);
        value["request_id"] = json::Value::String(request_id);
        let parsed = parse_request(&json::to_string(&value).unwrap()).unwrap();
        let result = dispatch_request(parsed);
        assert_eq!(result.status, "error");
        assert_eq!(result.error.as_deref(), Some("malformed-request"));
        assert!(result.request_id.is_none());
    }

    #[test]
    fn duplicate_unknown_and_invalid_utf8_are_malformed_and_recover() {
        let duplicate = format!(
            "{{\"protocol_id\":\"{}\",\"request_id\":\"dup\",\"request_id\":\"dup2\"}}\n",
            REQUEST_PROTOCOL_ID
        );
        let unknown = format!(
            "{}\n",
            json::to_string(&request_value(SOURCE))
                .unwrap()
                .trim_end()
                .replace("\"source\":", "\"unknown\":1,\"source\":",)
        );
        let input_bytes = [
            duplicate.into_bytes(),
            vec![0xff, b'\n'],
            unknown.into_bytes(),
        ]
        .concat();
        let mut input = BufReader::new(input_bytes.as_slice());
        let first = match read_input_frame(&mut input).unwrap() {
            InputFrame::Record(x) => process_record(&x),
            _ => panic!(),
        };
        assert_eq!(first.error.as_deref(), Some("malformed-request"));
        let second = match read_input_frame(&mut input).unwrap() {
            InputFrame::Record(x) => process_record(&x),
            _ => panic!(),
        };
        assert_eq!(second.error.as_deref(), Some("malformed-request"));
        let third = match read_input_frame(&mut input).unwrap() {
            InputFrame::Record(x) => process_record(&x),
            _ => panic!(),
        };
        assert_eq!(third.error.as_deref(), Some("malformed-request"));
    }
}
