//! Readiness 2 admission for the strict body-document source format.
//!
//! This module owns only source admission and bootstrap.  It deliberately does
//! not resolve references, normalize numbers, or acquire files.  The caller
//! supplies the complete source byte slice and the resource profile to apply.

use serde::de::{self, DeserializeSeed, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Deserializer, Serialize};
use serde_json::{Number, Value, value::RawValue};
use std::borrow::Borrow;
use std::cell::RefCell;
use std::collections::HashSet;
use std::fmt;
use std::rc::Rc;

/// The embedded, self-contained Draft 2020-12 schema for body documents.
pub const EMBEDDED_BODY_DOCUMENT_SCHEMA: &str =
    include_str!("../../../spec/body-document/schema/ck-body-document-v1.schema.json");

/// Ordinary Readiness 2 body-document resource profile identifier.
pub const ORDINARY_RESOURCE_PROFILE_ID: &str = "ck.resource.body.r2";
/// Tight profile used by the Readiness 2 resource fixture.
pub const TIGHT_RESOURCE_PROFILE_ID: &str = "ck.resource.body.r2-tight";
/// Readiness 2 diagnostic profile identifier.
pub const DIAGNOSTIC_PROFILE_ID: &str = "ck.diagnostic.r2";

/// Maximum source size for ordinary body-document admission.
pub const ORDINARY_MAX_SOURCE_BYTES: usize = 65_536;
/// Maximum source size for the deliberately tight fixture profile.
pub const TIGHT_MAX_SOURCE_BYTES: usize = 128;
/// Maximum JSON value nesting depth for the ordinary profile.
pub const ORDINARY_MAX_NESTING_DEPTH: usize = 64;
/// Maximum JSON value nesting depth for the tight profile.
pub const TIGHT_MAX_NESTING_DEPTH: usize = 64;
/// Maximum JSON values for the ordinary profile, including the root.
pub const ORDINARY_MAX_JSON_VALUES: usize = 8_192;
/// Maximum JSON values for the tight profile, including the root.
pub const TIGHT_MAX_JSON_VALUES: usize = 8_192;
/// Maximum aggregate object members for the ordinary profile.
pub const ORDINARY_MAX_OBJECT_MEMBERS: usize = 4_096;
/// Maximum aggregate object members for the tight profile.
pub const TIGHT_MAX_OBJECT_MEMBERS: usize = 4_096;
/// Maximum aggregate array entries for the ordinary profile.
pub const ORDINARY_MAX_ARRAY_ITEMS: usize = 4_096;
/// Maximum aggregate array entries for the tight profile.
pub const TIGHT_MAX_ARRAY_ITEMS: usize = 4_096;
/// Maximum decoded UTF-8 string/key bytes for the ordinary profile.
pub const ORDINARY_MAX_STRING_BYTES: usize = 16_384;
/// Maximum decoded UTF-8 string/key bytes for the tight profile.
pub const TIGHT_MAX_STRING_BYTES: usize = 16_384;
/// Maximum raw bytes in one JSON number token for the ordinary profile.
///
/// This bounds lexical work before a number is materialized by serde_json.
pub const ORDINARY_MAX_NUMBER_TOKEN_BYTES: usize = 256;
/// Maximum raw bytes in one JSON number token for the tight profile.
pub const TIGHT_MAX_NUMBER_TOKEN_BYTES: usize = 256;
/// Maximum retained independent diagnostics for the ordinary profile.
pub const ORDINARY_MAX_DIAGNOSTICS: usize = 64;
/// Maximum retained independent diagnostics for the tight profile.
pub const TIGHT_MAX_DIAGNOSTICS: usize = 64;

/// Resource profile supplied by the source-acquisition boundary.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ResourceProfile {
    id: &'static str,
    max_source_bytes: usize,
    max_nesting_depth: usize,
    max_json_values: usize,
    max_object_members: usize,
    max_array_items: usize,
    max_string_bytes: usize,
    max_number_token_bytes: usize,
    max_diagnostics: usize,
}

impl ResourceProfile {
    /// Ordinary body-document profile.
    pub const ORDINARY: Self = Self {
        id: ORDINARY_RESOURCE_PROFILE_ID,
        max_source_bytes: ORDINARY_MAX_SOURCE_BYTES,
        max_nesting_depth: ORDINARY_MAX_NESTING_DEPTH,
        max_json_values: ORDINARY_MAX_JSON_VALUES,
        max_object_members: ORDINARY_MAX_OBJECT_MEMBERS,
        max_array_items: ORDINARY_MAX_ARRAY_ITEMS,
        max_string_bytes: ORDINARY_MAX_STRING_BYTES,
        max_number_token_bytes: ORDINARY_MAX_NUMBER_TOKEN_BYTES,
        max_diagnostics: ORDINARY_MAX_DIAGNOSTICS,
    };

    /// Tight fixture profile.
    pub const TIGHT_FIXTURE: Self = Self {
        id: TIGHT_RESOURCE_PROFILE_ID,
        max_source_bytes: TIGHT_MAX_SOURCE_BYTES,
        max_nesting_depth: TIGHT_MAX_NESTING_DEPTH,
        max_json_values: TIGHT_MAX_JSON_VALUES,
        max_object_members: TIGHT_MAX_OBJECT_MEMBERS,
        max_array_items: TIGHT_MAX_ARRAY_ITEMS,
        max_string_bytes: TIGHT_MAX_STRING_BYTES,
        max_number_token_bytes: TIGHT_MAX_NUMBER_TOKEN_BYTES,
        max_diagnostics: TIGHT_MAX_DIAGNOSTICS,
    };
}

/// The ordinary Readiness 2 profile.
pub const ORDINARY_RESOURCE_PROFILE: ResourceProfile = ResourceProfile {
    ..ResourceProfile::ORDINARY
};

/// The tight Readiness 2 fixture profile.
pub const TIGHT_RESOURCE_PROFILE: ResourceProfile = ResourceProfile {
    ..ResourceProfile::TIGHT_FIXTURE
};

/// Alias for callers that want to make the fixture intent explicit.
pub const TIGHT_FIXTURE_RESOURCE_PROFILE: ResourceProfile = TIGHT_RESOURCE_PROFILE;

/// Closed top-level admission status algebra.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize, Serialize)]
#[serde(rename_all = "kebab-case")]
pub enum Status {
    Success,
    InvalidSource,
    Unsupported,
    ResourceLimit,
    InternalFailure,
}

/// Descriptive alias for callers that prefer the envelope terminology.
pub type AdmissionStatus = Status;

/// Stable diagnostic codes admitted by this Readiness 2 slice.
pub const CODE_RESOURCE_SOURCE_BYTES: &str = "ck.resource.source-bytes";
pub const CODE_RESOURCE_JSON_WORK: &str = "ck.resource.json-work";
pub const CODE_INVALID_JSON: &str = "ck.source.invalid-json";
pub const CODE_DUPLICATE_MEMBER: &str = "ck.source.duplicate-member";
pub const CODE_INVALID_DISCRIMINATOR: &str = "ck.contract.invalid-discriminator";
pub const CODE_UNSUPPORTED_FAMILY: &str = "ck.contract.unsupported-family";
pub const CODE_UNSUPPORTED_REVISION: &str = "ck.contract.unsupported-revision";
pub const CODE_SOURCE_SCHEMA: &str = "ck.source.schema";
pub const CODE_UNSUPPORTED_REQUIRED_EXTENSION: &str = "ck.extension.unsupported-required";
pub const CODE_INTERNAL_SCHEMA: &str = "ck.internal.schema";

/// One retained deterministic diagnostic occurrence.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Diagnostic {
    pub code: &'static str,
    pub message: String,
    pub instance_path: Option<String>,
    pub schema_path: Option<String>,
}

/// Authoritative result envelope for body-document admission.
#[derive(Debug, Clone, PartialEq)]
pub struct AdmissionResult {
    pub status: Status,
    pub processing_complete: bool,
    pub diagnostics_complete: bool,
    pub effective_diagnostic_profile_id: &'static str,
    pub effective_resource_profile_id: &'static str,
    pub primary_diagnostic: Option<Diagnostic>,
    pub diagnostics: Vec<Diagnostic>,
    pub document: Option<BodyDocument>,
}

impl AdmissionResult {
    /// Return the typed document when admission succeeded.
    #[must_use]
    pub fn as_document(&self) -> Option<&BodyDocument> {
        self.document.as_ref()
    }
}

/// Admit one complete strict body-document source against a resource profile.
pub fn admit_body_document<P: Borrow<ResourceProfile>>(
    source: &[u8],
    resource_profile: P,
) -> AdmissionResult {
    admit_impl(source, *resource_profile.borrow())
}

/// Short alias for [`admit_body_document`].
pub fn admit<P: Borrow<ResourceProfile>>(source: &[u8], resource_profile: P) -> AdmissionResult {
    admit_body_document(source, resource_profile)
}

/// Validate and compile the embedded schema without panicking.
pub fn validate_embedded_schema() -> Result<(), String> {
    compile_embedded_schema().map(|_| ())
}

/// Contract family admitted by this revision.
pub const BODY_CONTRACT_FAMILY: &str = "creature-kernel.body";
/// Contract revision admitted by this revision.
pub const BODY_CONTRACT_REVISION: u64 = 1;

/// The top-level body document.
#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct BodyDocument {
    pub contract: Contract,
    pub source: Source,
    pub basis: Basis,
    pub profiles: Profiles,
    pub body: Body,
    pub extensions: Vec<Extension>,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Contract {
    pub family: String,
    pub revision: Number,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Source {
    pub document: String,
    pub namespace: String,
    pub dependencies: Vec<Dependency>,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Dependency {
    pub document: String,
    pub namespace: String,
    pub content_sha256: String,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum LengthUnit {
    #[serde(rename = "millimetre")]
    Millimetre,
    #[serde(rename = "centimetre")]
    Centimetre,
    #[serde(rename = "metre")]
    Metre,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum Handedness {
    Left,
    Right,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
pub enum Axis {
    #[serde(rename = "+x")]
    PositiveX,
    #[serde(rename = "-x")]
    NegativeX,
    #[serde(rename = "+y")]
    PositiveY,
    #[serde(rename = "-y")]
    NegativeY,
    #[serde(rename = "+z")]
    PositiveZ,
    #[serde(rename = "-z")]
    NegativeZ,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Basis {
    pub length_unit: LengthUnit,
    pub handedness: Handedness,
    pub up: Axis,
    pub forward: Axis,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Profiles {
    pub semantic_numeric: String,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Extension {
    pub namespace: String,
    pub revision: Number,
    pub required: bool,
    pub payload: Value,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Body {
    pub modules: Vec<Module>,
    pub parts: Vec<Part>,
    pub joints: Vec<Joint>,
    pub sockets: Vec<Socket>,
    pub attachments: Vec<Attachment>,
    pub landmarks: Vec<Landmark>,
    pub dimensions: Vec<Dimension>,
    pub frames: Vec<Frame>,
    pub regions: Vec<Region>,
    pub capabilities: Vec<Capability>,
    pub fields: Vec<Field>,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Declaration {
    pub document: String,
    pub namespace: String,
    pub anchors: Vec<String>,
    pub role: String,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Module {
    pub declaration: Declaration,
    pub module: String,
    pub root_role: String,
    pub instance_anchor: String,
    pub presence: Presence,
    pub optional: bool,
    pub attachment_required: bool,
    pub root: Option<Address>,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum Presence {
    Absent,
    Present,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(untagged)]
pub enum Containment {
    Root { root: bool },
    Parent { parent: Address },
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Part {
    pub address: Address,
    pub containment: Containment,
    pub placement: RigidTransform,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Joint {
    pub address: Address,
    pub proximal: Address,
    pub distal: Address,
    pub proximal_frame: RigidTransform,
    pub distal_frame: RigidTransform,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Socket {
    pub address: Address,
    pub owner: Address,
    pub interface_frame: RigidTransform,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Attachment {
    pub address: Address,
    pub host: Address,
    pub mating: Address,
    pub offset: RigidTransform,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Landmark {
    pub owner: Address,
    pub role: String,
    pub frame: FrameRef,
    pub position: [Number; 3],
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Dimension {
    pub owner: Address,
    pub role: String,
    pub value: Number,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct FrameRef {
    pub owner: Address,
    pub role: String,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Frame {
    pub owner: Address,
    pub role: String,
    pub transform: RigidTransform,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Region {
    pub address: Address,
    pub parts: Vec<Address>,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Capability {
    pub address: Address,
    pub subjects: Vec<Address>,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Field {
    pub address: Address,
    pub owner: Address,
    pub frame: FrameRef,
    pub channel: String,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct RigidTransform {
    pub translation: [Number; 3],
    pub rotation_xyzw: [Number; 4],
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum AddressKind {
    Part,
    Joint,
    Socket,
    Attachment,
    Region,
    Capability,
    Field,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Address {
    pub namespace: String,
    pub anchors: Vec<String>,
    pub kind: AddressKind,
    pub role: String,
}

/// Address aliases retain the schema's typed record vocabulary while sharing
/// one engine-independent wire representation at this stage.
pub type PartAddress = Address;
pub type JointAddress = Address;
pub type SocketAddress = Address;
pub type AttachmentAddress = Address;
pub type RegionAddress = Address;
pub type CapabilityAddress = Address;
pub type FieldAddress = Address;

const DUPLICATE_ERROR_PREFIX: &str = "__ck_duplicate_member__";
const RESOURCE_ERROR_PREFIX: &str = "__ck_resource_json_work__";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum RawTokenScanError {
    Invalid,
    Resource,
}

/// A schema diagnostic's machine-facing structural identity.  Human-readable
/// messages are deliberately not part of this key or its ordering.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
struct DiagnosticKey {
    instance_path: String,
    schema_path: String,
    error_kind: String,
}

struct DiagnosticAccumulator {
    limit: usize,
    entries: Vec<(DiagnosticKey, Diagnostic)>,
    primary: Option<(DiagnosticKey, Diagnostic)>,
    saw_error: bool,
    truncated: bool,
}

impl DiagnosticAccumulator {
    fn new(limit: usize) -> Self {
        Self {
            limit,
            entries: Vec::new(),
            primary: None,
            saw_error: false,
            truncated: false,
        }
    }

    fn retain(&mut self, key: DiagnosticKey, diagnostic: Diagnostic) {
        self.saw_error = true;
        if self.entries.iter().any(|(existing, _)| *existing == key) {
            return;
        }
        if self
            .primary
            .as_ref()
            .is_none_or(|(primary_key, _)| key < *primary_key)
        {
            self.primary = Some((key.clone(), diagnostic.clone()));
        }
        if self.limit == 0 {
            self.truncated = true;
            return;
        }
        if self.entries.len() < self.limit {
            self.entries.push((key, diagnostic));
            return;
        }

        self.truncated = true;
    }

    fn finish(mut self) -> Option<(Vec<Diagnostic>, bool, Diagnostic)> {
        if !self.saw_error {
            return None;
        }
        self.entries.sort_by(|left, right| left.0.cmp(&right.0));
        let primary = self
            .primary
            .expect("an observed diagnostic always has a reserved primary");
        Some((
            self.entries
                .into_iter()
                .map(|(_, diagnostic)| diagnostic)
                .collect(),
            !self.truncated,
            primary.1,
        ))
    }
}

fn scan_raw_token_limits(
    source: &[u8],
    resource_profile: ResourceProfile,
) -> Result<(), RawTokenScanError> {
    let mut offset = 0;
    while offset < source.len() {
        match source[offset] {
            b'"' => {
                offset = match scan_raw_string(source, offset, resource_profile.max_string_bytes) {
                    Ok(end) => end,
                    Err(RawTokenScanError::Invalid) => return Err(RawTokenScanError::Invalid),
                    Err(RawTokenScanError::Resource) => return Err(RawTokenScanError::Resource),
                };
            }
            b'-' | b'0'..=b'9' => {
                if let Some(end) = scan_raw_number(source, offset) {
                    if end - offset > resource_profile.max_number_token_bytes {
                        return Err(RawTokenScanError::Resource);
                    }
                    offset = end;
                } else {
                    offset += 1;
                }
            }
            _ => offset += 1,
        }
    }
    Ok(())
}

fn scan_raw_string(
    source: &[u8],
    start: usize,
    max_decoded_bytes: usize,
) -> Result<usize, RawTokenScanError> {
    debug_assert_eq!(source.get(start), Some(&b'"'));
    let mut offset = start + 1;
    let mut decoded_bytes = 0usize;
    let mut too_large = false;
    while offset < source.len() {
        match source[offset] {
            b'"' => {
                return if too_large {
                    Err(RawTokenScanError::Resource)
                } else {
                    Ok(offset + 1)
                };
            }
            b'\\' => {
                offset += 1;
                let Some(escape) = source.get(offset).copied() else {
                    return Err(RawTokenScanError::Invalid);
                };
                match escape {
                    b'"' | b'\\' | b'/' | b'b' | b'f' | b'n' | b'r' | b't' => {
                        decoded_bytes = decoded_bytes.saturating_add(1);
                        offset += 1;
                    }
                    b'u' => {
                        let Some(unit) = parse_hex_quad(source, offset + 1) else {
                            return Err(RawTokenScanError::Invalid);
                        };
                        offset += 5;
                        if (0xD800..=0xDBFF).contains(&unit) {
                            if source.get(offset) != Some(&b'\\')
                                || source.get(offset + 1) != Some(&b'u')
                            {
                                return Err(RawTokenScanError::Invalid);
                            }
                            let Some(low) = parse_hex_quad(source, offset + 2) else {
                                return Err(RawTokenScanError::Invalid);
                            };
                            if !(0xDC00..=0xDFFF).contains(&low) {
                                return Err(RawTokenScanError::Invalid);
                            }
                            decoded_bytes = decoded_bytes.saturating_add(4);
                            offset += 6;
                        } else if (0xDC00..=0xDFFF).contains(&unit) {
                            return Err(RawTokenScanError::Invalid);
                        } else {
                            decoded_bytes = decoded_bytes.saturating_add(
                                char::from_u32(u32::from(unit)).unwrap().len_utf8(),
                            );
                        }
                        if decoded_bytes > max_decoded_bytes {
                            too_large = true;
                        }
                    }
                    _ => return Err(RawTokenScanError::Invalid),
                }
                if decoded_bytes > max_decoded_bytes {
                    too_large = true;
                }
            }
            byte if byte < 0x20 => return Err(RawTokenScanError::Invalid),
            _ => {
                let width = match source[offset] {
                    0x00..=0x7f => 1,
                    0xc2..=0xdf => 2,
                    0xe0..=0xef => 3,
                    0xf0..=0xf4 => 4,
                    _ => return Err(RawTokenScanError::Invalid),
                };
                let Some(end) = offset.checked_add(width) else {
                    return Err(RawTokenScanError::Invalid);
                };
                let Ok(text) = std::str::from_utf8(source.get(offset..end).unwrap_or_default())
                else {
                    return Err(RawTokenScanError::Invalid);
                };
                let Some(character) = text.chars().next() else {
                    return Err(RawTokenScanError::Invalid);
                };
                decoded_bytes = decoded_bytes.saturating_add(character.len_utf8());
                if decoded_bytes > max_decoded_bytes {
                    too_large = true;
                }
                offset += character.len_utf8();
            }
        }
    }
    Err(RawTokenScanError::Invalid)
}

fn parse_hex_quad(source: &[u8], start: usize) -> Option<u16> {
    let digits = source.get(start..start + 4)?;
    let mut value = 0u16;
    for digit in digits {
        value = value.checked_mul(16)?.checked_add(match digit {
            b'0'..=b'9' => u16::from(*digit - b'0'),
            b'a'..=b'f' => u16::from(*digit - b'a' + 10),
            b'A'..=b'F' => u16::from(*digit - b'A' + 10),
            _ => return None,
        })?;
    }
    Some(value)
}

fn scan_raw_number(source: &[u8], start: usize) -> Option<usize> {
    let mut offset = start;
    if source.get(offset) == Some(&b'-') {
        offset += 1;
    }
    match source.get(offset).copied()? {
        b'0' => offset += 1,
        b'1'..=b'9' => {
            offset += 1;
            while matches!(source.get(offset), Some(b'0'..=b'9')) {
                offset += 1;
            }
        }
        _ => return None,
    }
    if source.get(offset) == Some(&b'.') {
        offset += 1;
        let fraction_start = offset;
        while matches!(source.get(offset), Some(b'0'..=b'9')) {
            offset += 1;
        }
        if offset == fraction_start {
            return None;
        }
    }
    if matches!(source.get(offset), Some(b'e' | b'E')) {
        offset += 1;
        if matches!(source.get(offset), Some(b'+' | b'-')) {
            offset += 1;
        }
        let exponent_start = offset;
        while matches!(source.get(offset), Some(b'0'..=b'9')) {
            offset += 1;
        }
        if offset == exponent_start {
            return None;
        }
    }
    if source
        .get(offset)
        .is_some_and(|byte| !matches!(byte, b' ' | b'\n' | b'\r' | b'\t' | b',' | b']' | b'}'))
    {
        return None;
    }
    Some(offset)
}

fn decimal_number_equals_one(token: &str) -> bool {
    let (mantissa, exponent) = if let Some((mantissa, exponent)) =
        token.split_once('e').or_else(|| token.split_once('E'))
    {
        let Some(exponent) = exponent.parse::<i64>().ok() else {
            return false;
        };
        (mantissa, exponent)
    } else {
        (token, 0)
    };
    if mantissa.starts_with('-') {
        return false;
    }
    let mut fractional_digits = 0i64;
    let mut in_fraction = false;
    let mut digit_count = 0i64;
    let mut first_nonzero = None;
    for byte in mantissa.bytes() {
        if byte == b'.' {
            in_fraction = true;
            continue;
        }
        if !byte.is_ascii_digit() {
            return false;
        }
        if in_fraction {
            fractional_digits += 1;
        }
        if byte != b'0' {
            if byte != b'1' || first_nonzero.is_some() {
                return false;
            }
            first_nonzero = Some(digit_count);
        }
        digit_count += 1;
    }
    let Some(first_nonzero) = first_nonzero else {
        return false;
    };
    let trailing_zero_digits = digit_count - first_nonzero - 1;
    trailing_zero_digits + exponent - fractional_digits == 0
}

fn admit_impl(source: &[u8], resource_profile: ResourceProfile) -> AdmissionResult {
    if source.len() > resource_profile.max_source_bytes {
        return failure(
            Status::ResourceLimit,
            resource_profile,
            CODE_RESOURCE_SOURCE_BYTES,
            "source exceeds the configured raw-byte limit",
            None,
            false,
        );
    }

    // Validate the complete JSON grammar without materializing strings,
    // numbers, or object values.  This must precede the resource scanner so a
    // malformed numeric-looking suffix or leading-zero form cannot be
    // reinterpreted as an oversized valid token.
    if validate_json_grammar(source).is_err() {
        return failure(
            Status::InvalidSource,
            resource_profile,
            CODE_INVALID_JSON,
            "source is not strict UTF-8 JSON",
            None,
            true,
        );
    }

    // Check token lengths against the raw source before serde_json can allocate
    // decoded strings/keys or materialize number representations.
    if matches!(
        scan_raw_token_limits(source, resource_profile),
        Err(RawTokenScanError::Resource)
    ) {
        return failure(
            Status::ResourceLimit,
            resource_profile,
            CODE_RESOURCE_JSON_WORK,
            "source exceeds the configured JSON token limits",
            None,
            false,
        );
    }

    if let Err(error) = detect_duplicates(source, resource_profile) {
        let text = error.to_string();
        if text.starts_with(DUPLICATE_ERROR_PREFIX) {
            let path = text
                .strip_prefix(DUPLICATE_ERROR_PREFIX)
                .map(ToOwned::to_owned);
            return failure_with_paths(
                Status::InvalidSource,
                resource_profile,
                CODE_DUPLICATE_MEMBER,
                "duplicate JSON object member",
                path,
                None,
                true,
            );
        }
        if text.starts_with(RESOURCE_ERROR_PREFIX) {
            let path = text
                .strip_prefix(RESOURCE_ERROR_PREFIX)
                .map(ToOwned::to_owned);
            return failure_with_paths(
                Status::ResourceLimit,
                resource_profile,
                CODE_RESOURCE_JSON_WORK,
                "source exceeds the configured JSON work limits",
                path,
                None,
                false,
            );
        }
        return failure(
            Status::InvalidSource,
            resource_profile,
            CODE_INVALID_JSON,
            "source is not strict UTF-8 JSON",
            None,
            true,
        );
    }

    let value = match parse_value(source) {
        Ok(value) => value,
        Err(_) => {
            return failure(
                Status::InvalidSource,
                resource_profile,
                CODE_INVALID_JSON,
                "source is not strict UTF-8 JSON",
                None,
                true,
            );
        }
    };

    let Some(object) = value.as_object() else {
        return failure(
            Status::InvalidSource,
            resource_profile,
            CODE_INVALID_DISCRIMINATOR,
            "contract discriminator must be a top-level object",
            None,
            true,
        );
    };

    let Some(contract) = object.get("contract").and_then(Value::as_object) else {
        return failure(
            Status::InvalidSource,
            resource_profile,
            CODE_INVALID_DISCRIMINATOR,
            "contract discriminator is missing or malformed",
            None,
            true,
        );
    };
    if contract.len() != 2 || !contract.contains_key("family") || !contract.contains_key("revision")
    {
        return failure(
            Status::InvalidSource,
            resource_profile,
            CODE_INVALID_DISCRIMINATOR,
            "contract discriminator must contain exactly family and revision",
            None,
            true,
        );
    }
    let Some(family) = contract.get("family").and_then(Value::as_str) else {
        return failure(
            Status::InvalidSource,
            resource_profile,
            CODE_INVALID_DISCRIMINATOR,
            "contract family discriminator is missing or malformed",
            None,
            true,
        );
    };
    let Some(revision) = contract.get("revision").and_then(Value::as_number) else {
        return failure(
            Status::InvalidSource,
            resource_profile,
            CODE_INVALID_DISCRIMINATOR,
            "contract revision discriminator is missing or malformed",
            None,
            true,
        );
    };

    if family != BODY_CONTRACT_FAMILY {
        return failure(
            Status::Unsupported,
            resource_profile,
            CODE_UNSUPPORTED_FAMILY,
            "contract family is not supported",
            None,
            true,
        );
    }
    if !is_revision_one(revision) {
        return failure(
            Status::Unsupported,
            resource_profile,
            CODE_UNSUPPORTED_REVISION,
            "contract revision is not supported",
            None,
            true,
        );
    }

    let validator = match compile_embedded_schema() {
        Ok(validator) => validator,
        Err(_) => {
            return failure(
                Status::InternalFailure,
                resource_profile,
                CODE_INTERNAL_SCHEMA,
                "embedded body-document schema could not be compiled",
                None,
                false,
            );
        }
    };

    let mut schema_diagnostics = DiagnosticAccumulator::new(resource_profile.max_diagnostics);
    for error in validator.iter_errors(&value) {
        let key = DiagnosticKey {
            instance_path: error.instance_path().to_string(),
            schema_path: error.schema_path().to_string(),
            error_kind: error.kind().keyword().to_owned(),
        };
        schema_diagnostics.retain(
            key,
            Diagnostic {
                code: CODE_SOURCE_SCHEMA,
                message: error.to_string(),
                instance_path: Some(error.instance_path().to_string()),
                schema_path: Some(error.schema_path().to_string()),
            },
        );
    }
    if let Some((diagnostics, diagnostics_complete, primary_diagnostic)) =
        schema_diagnostics.finish()
    {
        return failure_with_diagnostics(
            Status::InvalidSource,
            resource_profile,
            diagnostics,
            diagnostics_complete,
            true,
            primary_diagnostic,
        );
    }

    let document = match serde_json::from_value::<BodyDocument>(value) {
        Ok(document) => document,
        Err(error) => {
            return failure(
                Status::InvalidSource,
                resource_profile,
                CODE_SOURCE_SCHEMA,
                format!("typed body-document deserialization failed: {error}"),
                None,
                true,
            );
        }
    };

    if document
        .extensions
        .iter()
        .any(|extension| extension.required)
    {
        return failure(
            Status::Unsupported,
            resource_profile,
            CODE_UNSUPPORTED_REQUIRED_EXTENSION,
            "a required extension is not supported",
            None,
            true,
        );
    }

    AdmissionResult {
        status: Status::Success,
        processing_complete: true,
        diagnostics_complete: true,
        effective_diagnostic_profile_id: DIAGNOSTIC_PROFILE_ID,
        effective_resource_profile_id: resource_profile.id,
        primary_diagnostic: None,
        diagnostics: Vec::new(),
        document: Some(document),
    }
}

fn is_revision_one(number: &Number) -> bool {
    decimal_number_equals_one(&number.to_string())
}

fn failure(
    status: Status,
    resource_profile: ResourceProfile,
    code: &'static str,
    message: impl Into<String>,
    path: Option<String>,
    processing_complete: bool,
) -> AdmissionResult {
    failure_with_paths(
        status,
        resource_profile,
        code,
        message,
        path,
        None,
        processing_complete,
    )
}

fn failure_with_paths(
    status: Status,
    resource_profile: ResourceProfile,
    code: &'static str,
    message: impl Into<String>,
    instance_path: Option<String>,
    schema_path: Option<String>,
    processing_complete: bool,
) -> AdmissionResult {
    let diagnostic = Diagnostic {
        code,
        message: message.into(),
        instance_path,
        schema_path,
    };
    AdmissionResult {
        status,
        processing_complete,
        diagnostics_complete: true,
        effective_diagnostic_profile_id: DIAGNOSTIC_PROFILE_ID,
        effective_resource_profile_id: resource_profile.id,
        primary_diagnostic: Some(diagnostic.clone()),
        diagnostics: vec![diagnostic],
        document: None,
    }
}

fn failure_with_diagnostics(
    status: Status,
    resource_profile: ResourceProfile,
    diagnostics: Vec<Diagnostic>,
    diagnostics_complete: bool,
    processing_complete: bool,
    primary_diagnostic: Diagnostic,
) -> AdmissionResult {
    AdmissionResult {
        status,
        processing_complete,
        diagnostics_complete,
        effective_diagnostic_profile_id: DIAGNOSTIC_PROFILE_ID,
        effective_resource_profile_id: resource_profile.id,
        primary_diagnostic: Some(primary_diagnostic),
        diagnostics,
        document: None,
    }
}

fn validate_json_grammar(source: &[u8]) -> Result<(), serde_json::Error> {
    serde_json::from_slice::<&RawValue>(source).map(|_| ())
}

fn parse_value(source: &[u8]) -> Result<Value, serde_json::Error> {
    let mut deserializer = serde_json::Deserializer::from_slice(source);
    let value = Value::deserialize(&mut deserializer)?;
    deserializer.end()?;
    Ok(value)
}

fn detect_duplicates(
    source: &[u8],
    resource_profile: ResourceProfile,
) -> Result<(), serde_json::Error> {
    let mut deserializer = serde_json::Deserializer::from_slice(source);
    DuplicateSeed::root(resource_profile).deserialize(&mut deserializer)?;
    deserializer.end()
}

#[derive(Debug, Clone, Copy)]
enum ResourceBreach {
    NestingDepth,
    JsonValues,
    ObjectMembers,
    ArrayItems,
    StringBytes,
}

#[derive(Debug)]
struct JsonBudget {
    profile: ResourceProfile,
    json_values: usize,
    object_members: usize,
    array_items: usize,
}

impl JsonBudget {
    fn new(profile: ResourceProfile) -> Self {
        Self {
            profile,
            json_values: 0,
            object_members: 0,
            array_items: 0,
        }
    }

    fn admit_value(&mut self, depth: usize) -> Result<(), ResourceBreach> {
        if depth > self.profile.max_nesting_depth {
            return Err(ResourceBreach::NestingDepth);
        }
        if self.json_values >= self.profile.max_json_values {
            return Err(ResourceBreach::JsonValues);
        }
        self.json_values += 1;
        Ok(())
    }

    fn admit_object_member(&mut self) -> Result<(), ResourceBreach> {
        if self.object_members >= self.profile.max_object_members {
            return Err(ResourceBreach::ObjectMembers);
        }
        self.object_members += 1;
        Ok(())
    }

    fn admit_array_item(&mut self) -> Result<(), ResourceBreach> {
        if self.array_items >= self.profile.max_array_items {
            return Err(ResourceBreach::ArrayItems);
        }
        self.array_items += 1;
        Ok(())
    }

    fn admit_string(&mut self, bytes: usize) -> Result<(), ResourceBreach> {
        if bytes > self.profile.max_string_bytes {
            return Err(ResourceBreach::StringBytes);
        }
        Ok(())
    }
}

#[derive(Clone)]
struct DuplicateSeed {
    path: String,
    depth: usize,
    array_item: bool,
    budget: Rc<RefCell<JsonBudget>>,
}

impl DuplicateSeed {
    fn root(resource_profile: ResourceProfile) -> Self {
        Self {
            path: String::new(),
            depth: 1,
            array_item: false,
            budget: Rc::new(RefCell::new(JsonBudget::new(resource_profile))),
        }
    }

    fn child(&self, segment: &str) -> Self {
        let mut path = self.path.clone();
        path.push('/');
        append_pointer_segment(&mut path, segment);
        Self {
            path,
            depth: self.depth + 1,
            array_item: false,
            budget: Rc::clone(&self.budget),
        }
    }

    fn index_child(&self, index: usize) -> Self {
        let mut child = self.child(&index.to_string());
        child.array_item = true;
        child
    }

    fn resource_error(&self, _breach: ResourceBreach) -> String {
        format!("{RESOURCE_ERROR_PREFIX}{}", self.path)
    }

    fn admit_value<E>(&self) -> Result<(), E>
    where
        E: de::Error,
    {
        let result = {
            let mut budget = self.budget.borrow_mut();
            if self.array_item {
                budget.admit_array_item()
            } else {
                Ok(())
            }
        };
        if let Err(breach) = result {
            return Err(E::custom(self.resource_error(breach)));
        }

        let result = self.budget.borrow_mut().admit_value(self.depth);
        result.map_err(|breach| E::custom(self.resource_error(breach)))
    }

    fn admit_string<E>(&self, bytes: usize) -> Result<(), E>
    where
        E: de::Error,
    {
        let result = self.budget.borrow_mut().admit_string(bytes);
        result.map_err(|breach| E::custom(self.resource_error(breach)))
    }
}

impl<'de> DeserializeSeed<'de> for DuplicateSeed {
    type Value = ();

    fn deserialize<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: Deserializer<'de>,
    {
        self.admit_value::<D::Error>()?;
        deserializer.deserialize_any(DuplicateVisitor { seed: self })
    }
}

struct DuplicateVisitor {
    seed: DuplicateSeed,
}

impl<'de> Visitor<'de> for DuplicateVisitor {
    type Value = ();

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("a strict JSON value")
    }

    fn visit_unit<E>(self) -> Result<Self::Value, E> {
        Ok(())
    }

    fn visit_bool<E>(self, _value: bool) -> Result<Self::Value, E> {
        Ok(())
    }

    fn visit_i64<E>(self, _value: i64) -> Result<Self::Value, E> {
        Ok(())
    }

    fn visit_i128<E>(self, _value: i128) -> Result<Self::Value, E> {
        Ok(())
    }

    fn visit_u64<E>(self, _value: u64) -> Result<Self::Value, E> {
        Ok(())
    }

    fn visit_u128<E>(self, _value: u128) -> Result<Self::Value, E> {
        Ok(())
    }

    fn visit_f32<E>(self, _value: f32) -> Result<Self::Value, E> {
        Ok(())
    }

    fn visit_f64<E>(self, _value: f64) -> Result<Self::Value, E> {
        Ok(())
    }

    fn visit_str<E>(self, value: &str) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        self.seed.admit_string::<E>(value.len())
    }

    fn visit_borrowed_str<E>(self, value: &'de str) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        self.seed.admit_string::<E>(value.len())
    }

    fn visit_string<E>(self, value: String) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        self.seed.admit_string::<E>(value.len())
    }

    fn visit_bytes<E>(self, value: &[u8]) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        self.seed.admit_string::<E>(value.len())
    }

    fn visit_byte_buf<E>(self, value: Vec<u8>) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        self.seed.admit_string::<E>(value.len())
    }

    fn visit_none<E>(self) -> Result<Self::Value, E> {
        Ok(())
    }

    fn visit_some<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: Deserializer<'de>,
    {
        DuplicateSeed::deserialize(self.seed, deserializer)
    }

    fn visit_newtype_struct<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: Deserializer<'de>,
    {
        DuplicateSeed::deserialize(self.seed, deserializer)
    }

    fn visit_seq<A>(self, mut sequence: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let mut index = 0;
        while sequence
            .next_element_seed(self.seed.index_child(index))?
            .is_some()
        {
            index += 1;
        }
        Ok(())
    }

    fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut members = HashSet::new();
        while let Some(key) = map.next_key::<String>()? {
            if members.contains(key.as_str()) {
                return Err(de::Error::custom(format!(
                    "{DUPLICATE_ERROR_PREFIX}{}",
                    self.seed.child(&key).path
                )));
            }
            let member_result = {
                let mut budget = self.seed.budget.borrow_mut();
                match budget.admit_object_member() {
                    Ok(()) => budget.admit_string(key.len()),
                    Err(breach) => Err(breach),
                }
            };
            if let Err(breach) = member_result {
                return Err(de::Error::custom(self.seed.resource_error(breach)));
            }
            members.insert(key.clone());
            let child = self.seed.child(&key);
            map.next_value_seed(child)?;
        }
        Ok(())
    }
}

fn append_pointer_segment(path: &mut String, segment: &str) {
    for character in segment.chars() {
        match character {
            '~' => path.push_str("~0"),
            '/' => path.push_str("~1"),
            character => path.push(character),
        }
    }
}

fn compile_embedded_schema() -> Result<jsonschema::Validator, String> {
    let schema: Value = serde_json::from_str(EMBEDDED_BODY_DOCUMENT_SCHEMA)
        .map_err(|error| format!("embedded schema JSON is invalid: {error}"))?;
    jsonschema::draft202012::options()
        .build(&schema)
        .map_err(|error| format!("embedded schema compilation failed: {error}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Deserialize)]
    struct FixtureManifest {
        fixtures: Vec<ManifestFixture>,
    }

    #[derive(Deserialize)]
    struct ManifestFixture {
        id: String,
        profiles: ManifestProfiles,
        expected: ManifestExpected,
    }

    #[derive(Deserialize)]
    struct ManifestProfiles {
        resource: String,
    }

    #[derive(Deserialize)]
    struct ManifestExpected {
        status: Status,
        processing_complete: bool,
        diagnostics_complete: bool,
        primary_diagnostic: Option<String>,
    }

    fn fixture(name: &str) -> Vec<u8> {
        match name {
            "duplicate-member" => {
                include_bytes!("../../../fixtures/body-documents/readiness-2/duplicate-member.json")
                    .to_vec()
            }
            "invalid-discriminator" => include_bytes!(
                "../../../fixtures/body-documents/readiness-2/invalid-discriminator.json"
            )
            .to_vec(),
            "minimal-valid-envelope" => include_bytes!(
                "../../../fixtures/body-documents/readiness-2/minimal-valid-envelope.json"
            )
            .to_vec(),
            "optional-extension-opaque" => include_bytes!(
                "../../../fixtures/body-documents/readiness-2/optional-extension-opaque.json"
            )
            .to_vec(),
            "optional-module-absent" => include_bytes!(
                "../../../fixtures/body-documents/readiness-2/optional-module-absent.json"
            )
            .to_vec(),
            "resource-over-budget" => include_bytes!(
                "../../../fixtures/body-documents/readiness-2/resource-over-budget.json"
            )
            .to_vec(),
            "unknown-core-member" => include_bytes!(
                "../../../fixtures/body-documents/readiness-2/unknown-core-member.json"
            )
            .to_vec(),
            "unsupported-required-extension" => include_bytes!(
                "../../../fixtures/body-documents/readiness-2/unsupported-required-extension.json"
            )
            .to_vec(),
            "unsupported-revision" => include_bytes!(
                "../../../fixtures/body-documents/readiness-2/unsupported-revision.json"
            )
            .to_vec(),
            _ => panic!("unknown fixture {name}"),
        }
    }

    fn assert_primary(result: &AdmissionResult, code: &str) {
        assert_eq!(
            result.primary_diagnostic.as_ref().map(|d| d.code),
            Some(code)
        );
        assert!(
            result
                .diagnostics
                .iter()
                .any(|diagnostic| diagnostic.code == code)
        );
        assert!(result.document.is_none());
    }

    fn admit_fixture(name: &str, profile: ResourceProfile) -> AdmissionResult {
        let source = fixture(name);
        admit_body_document(&source, profile)
    }

    fn assert_json_resource_limit(source: &[u8]) {
        let result = admit_body_document(source, ORDINARY_RESOURCE_PROFILE);
        assert_eq!(result.status, Status::ResourceLimit);
        assert!(!result.processing_complete);
        assert!(result.diagnostics_complete);
        assert_primary(&result, CODE_RESOURCE_JSON_WORK);
    }

    fn nested_null_at_depth(depth: usize) -> Vec<u8> {
        let mut source = Vec::with_capacity(depth * 2 + 4);
        source.extend(std::iter::repeat_n(b'[', depth - 1));
        source.extend_from_slice(b"null");
        source.extend(std::iter::repeat_n(b']', depth - 1));
        source
    }

    fn array_of_objects(with_last_member: bool) -> Vec<u8> {
        let mut source = Vec::new();
        source.push(b'[');
        for index in 0..ORDINARY_MAX_ARRAY_ITEMS {
            if index != 0 {
                source.push(b',');
            }
            if with_last_member || index + 1 != ORDINARY_MAX_ARRAY_ITEMS {
                source.extend_from_slice(br#"{"x":null}"#);
            } else {
                source.extend_from_slice(b"{}");
            }
        }
        source.push(b']');
        source
    }

    fn object_with_members(count: usize) -> Vec<u8> {
        let mut source = Vec::new();
        source.push(b'{');
        for index in 0..count {
            if index != 0 {
                source.push(b',');
            }
            source.extend_from_slice(format!("\"k{index}\":null").as_bytes());
        }
        source.push(b'}');
        source
    }

    fn string_with_decoded_bytes(bytes: usize) -> String {
        let mut value = "é".repeat(bytes / 2);
        if !bytes.is_multiple_of(2) {
            value.push('a');
        }
        assert_eq!(value.len(), bytes);
        value
    }

    fn object_with_key_bytes(bytes: usize) -> Vec<u8> {
        let key = string_with_decoded_bytes(bytes);
        let mut source = Vec::new();
        source.push(b'{');
        source.extend_from_slice(serde_json::to_string(&key).unwrap().as_bytes());
        source.extend_from_slice(b":null}");
        source
    }

    fn source_with_revision_token(token: &str) -> Vec<u8> {
        let source = String::from_utf8(fixture("minimal-valid-envelope")).unwrap();
        source
            .replacen("\"revision\": 1", &format!("\"revision\": {token}"), 1)
            .into_bytes()
    }

    #[test]
    fn all_nine_fixtures_have_the_expected_bootstrap_outcomes() {
        let success = admit_fixture("minimal-valid-envelope", ORDINARY_RESOURCE_PROFILE);
        assert_eq!(success.status, Status::Success);
        assert!(success.processing_complete);
        assert!(success.diagnostics_complete);
        assert!(success.primary_diagnostic.is_none());
        assert!(success.diagnostics.is_empty());
        assert!(success.document.is_some());

        let optional_module = admit_fixture("optional-module-absent", ORDINARY_RESOURCE_PROFILE);
        assert_eq!(optional_module.status, Status::Success);
        assert_eq!(optional_module.document.unwrap().body.modules.len(), 1);

        let optional_extension =
            admit_fixture("optional-extension-opaque", ORDINARY_RESOURCE_PROFILE);
        assert_eq!(optional_extension.status, Status::Success);
        assert!(
            optional_extension.document.unwrap().extensions[0]
                .payload
                .is_object()
        );

        let duplicate = admit_fixture("duplicate-member", ORDINARY_RESOURCE_PROFILE);
        assert_eq!(duplicate.status, Status::InvalidSource);
        assert_primary(&duplicate, CODE_DUPLICATE_MEMBER);

        let malformed = admit_fixture("invalid-discriminator", ORDINARY_RESOURCE_PROFILE);
        assert_eq!(malformed.status, Status::InvalidSource);
        assert_primary(&malformed, CODE_INVALID_DISCRIMINATOR);

        let unknown_core = admit_fixture("unknown-core-member", ORDINARY_RESOURCE_PROFILE);
        assert_eq!(unknown_core.status, Status::InvalidSource);
        assert_primary(&unknown_core, CODE_SOURCE_SCHEMA);

        let revision = admit_fixture("unsupported-revision", ORDINARY_RESOURCE_PROFILE);
        assert_eq!(revision.status, Status::Unsupported);
        assert_primary(&revision, CODE_UNSUPPORTED_REVISION);

        let required_extension =
            admit_fixture("unsupported-required-extension", ORDINARY_RESOURCE_PROFILE);
        assert_eq!(required_extension.status, Status::Unsupported);
        assert_primary(&required_extension, CODE_UNSUPPORTED_REQUIRED_EXTENSION);

        let resource = admit_fixture("resource-over-budget", TIGHT_RESOURCE_PROFILE);
        assert_eq!(resource.status, Status::ResourceLimit);
        assert!(!resource.processing_complete);
        assert_primary(&resource, CODE_RESOURCE_SOURCE_BYTES);
    }

    #[test]
    fn all_manifest_expectations_match_the_parser() {
        let manifest: FixtureManifest = serde_json::from_str(include_str!(
            "../../../fixtures/body-documents/readiness-2/manifest.v1.json"
        ))
        .unwrap();
        assert_eq!(manifest.fixtures.len(), 9);

        for entry in manifest.fixtures {
            let profile = match entry.profiles.resource.as_str() {
                ORDINARY_RESOURCE_PROFILE_ID => ORDINARY_RESOURCE_PROFILE,
                TIGHT_RESOURCE_PROFILE_ID => TIGHT_RESOURCE_PROFILE,
                other => panic!("unrecognized manifest resource profile {other}"),
            };
            let result = admit_fixture(&entry.id, profile);
            assert_eq!(result.status, entry.expected.status, "{}", entry.id);
            assert_eq!(
                result.processing_complete, entry.expected.processing_complete,
                "{}",
                entry.id
            );
            assert_eq!(
                result.diagnostics_complete, entry.expected.diagnostics_complete,
                "{}",
                entry.id
            );
            assert_eq!(
                result.primary_diagnostic.as_ref().map(|item| item.code),
                entry.expected.primary_diagnostic.as_deref(),
                "{}",
                entry.id
            );
        }
    }

    #[test]
    fn profile_ids_and_success_failure_primary_invariants_are_closed() {
        let result = admit_fixture("minimal-valid-envelope", TIGHT_RESOURCE_PROFILE);
        assert_eq!(
            result.effective_diagnostic_profile_id,
            DIAGNOSTIC_PROFILE_ID
        );
        assert_eq!(
            result.effective_resource_profile_id,
            TIGHT_RESOURCE_PROFILE_ID
        );
        assert!(result.document.is_none());
        assert!(result.primary_diagnostic.is_some());

        let result = admit_fixture("minimal-valid-envelope", ORDINARY_RESOURCE_PROFILE);
        assert_eq!(
            result.effective_diagnostic_profile_id,
            DIAGNOSTIC_PROFILE_ID
        );
        assert_eq!(
            result.effective_resource_profile_id,
            ORDINARY_RESOURCE_PROFILE_ID
        );
        assert!(result.primary_diagnostic.is_none());
        assert!(result.document.is_some());
    }

    #[test]
    fn nested_duplicates_are_rejected_before_materialization() {
        let source = br#"{"contract":{"family":"creature-kernel.body","revision":1},"source":{"document":"main","document":"main"}}"#;
        let result = admit_body_document(source, ORDINARY_RESOURCE_PROFILE);
        assert_eq!(result.status, Status::InvalidSource);
        assert_primary(&result, CODE_DUPLICATE_MEMBER);
    }

    #[test]
    fn malformed_syntax_and_invalid_utf8_are_invalid_source() {
        let malformed = admit_body_document(br#"{"#, ORDINARY_RESOURCE_PROFILE);
        assert_eq!(malformed.status, Status::InvalidSource);
        assert_primary(&malformed, CODE_INVALID_JSON);

        let invalid_utf8 = admit_body_document(b"{\xff", ORDINARY_RESOURCE_PROFILE);
        assert_eq!(invalid_utf8.status, Status::InvalidSource);
        assert_primary(&invalid_utf8, CODE_INVALID_JSON);
    }

    #[test]
    fn unknown_family_is_unsupported_before_schema() {
        let mut value: Value = serde_json::from_slice(&fixture("minimal-valid-envelope")).unwrap();
        value["contract"]["family"] = Value::String("other.family".to_owned());
        let source = serde_json::to_vec(&value).unwrap();
        let result = admit_body_document(&source, ORDINARY_RESOURCE_PROFILE);
        assert_eq!(result.status, Status::Unsupported);
        assert_primary(&result, CODE_UNSUPPORTED_FAMILY);
    }

    #[test]
    fn exact_resource_boundary_is_admitted_for_parsing() {
        let source = vec![b' '; TIGHT_MAX_SOURCE_BYTES];
        let result = admit_body_document(&source, TIGHT_RESOURCE_PROFILE);
        assert_eq!(result.status, Status::InvalidSource);
        assert!(result.processing_complete);
        assert_primary(&result, CODE_INVALID_JSON);
    }

    #[test]
    fn json_resource_profile_limits_are_public_and_equal_across_profiles() {
        assert_eq!(ORDINARY_RESOURCE_PROFILE.max_nesting_depth, 64);
        assert_eq!(TIGHT_RESOURCE_PROFILE.max_nesting_depth, 64);
        assert_eq!(ORDINARY_RESOURCE_PROFILE.max_json_values, 8_192);
        assert_eq!(TIGHT_RESOURCE_PROFILE.max_json_values, 8_192);
        assert_eq!(ORDINARY_RESOURCE_PROFILE.max_object_members, 4_096);
        assert_eq!(TIGHT_RESOURCE_PROFILE.max_object_members, 4_096);
        assert_eq!(ORDINARY_RESOURCE_PROFILE.max_array_items, 4_096);
        assert_eq!(TIGHT_RESOURCE_PROFILE.max_array_items, 4_096);
        assert_eq!(ORDINARY_RESOURCE_PROFILE.max_string_bytes, 16_384);
        assert_eq!(TIGHT_RESOURCE_PROFILE.max_string_bytes, 16_384);
        assert_eq!(ORDINARY_RESOURCE_PROFILE.max_number_token_bytes, 256);
        assert_eq!(TIGHT_RESOURCE_PROFILE.max_number_token_bytes, 256);
        assert_eq!(ORDINARY_RESOURCE_PROFILE.max_diagnostics, 64);
        assert_eq!(TIGHT_RESOURCE_PROFILE.max_diagnostics, 64);
        assert_eq!(
            ORDINARY_RESOURCE_PROFILE.max_number_token_bytes,
            ORDINARY_MAX_NUMBER_TOKEN_BYTES
        );
        assert_eq!(
            TIGHT_RESOURCE_PROFILE.max_number_token_bytes,
            TIGHT_MAX_NUMBER_TOKEN_BYTES
        );
        assert_eq!(
            ORDINARY_RESOURCE_PROFILE.max_diagnostics,
            ORDINARY_MAX_DIAGNOSTICS
        );
        assert_eq!(
            TIGHT_RESOURCE_PROFILE.max_diagnostics,
            TIGHT_MAX_DIAGNOSTICS
        );
    }

    #[test]
    fn nesting_depth_boundary_is_checked_before_materialization() {
        let at_boundary = admit_body_document(
            &nested_null_at_depth(ORDINARY_MAX_NESTING_DEPTH),
            ORDINARY_RESOURCE_PROFILE,
        );
        assert_eq!(at_boundary.status, Status::InvalidSource);
        assert!(at_boundary.processing_complete);
        assert_primary(&at_boundary, CODE_INVALID_DISCRIMINATOR);

        assert_json_resource_limit(&nested_null_at_depth(ORDINARY_MAX_NESTING_DEPTH + 1));
    }

    #[test]
    fn aggregate_json_value_limit_is_enforced() {
        let at_boundary = admit_body_document(&array_of_objects(false), ORDINARY_RESOURCE_PROFILE);
        assert_eq!(at_boundary.status, Status::InvalidSource);
        assert!(at_boundary.processing_complete);
        assert_primary(&at_boundary, CODE_INVALID_DISCRIMINATOR);

        assert_json_resource_limit(&array_of_objects(true));
    }

    #[test]
    fn aggregate_object_member_limit_is_enforced() {
        let at_boundary = admit_body_document(
            &object_with_members(ORDINARY_MAX_OBJECT_MEMBERS),
            ORDINARY_RESOURCE_PROFILE,
        );
        assert_eq!(at_boundary.status, Status::InvalidSource);
        assert!(at_boundary.processing_complete);
        assert_primary(&at_boundary, CODE_INVALID_DISCRIMINATOR);

        assert_json_resource_limit(&object_with_members(ORDINARY_MAX_OBJECT_MEMBERS + 1));
    }

    #[test]
    fn aggregate_array_item_limit_is_enforced() {
        let at_boundary = admit_body_document(
            &format!(
                "[{}]",
                std::iter::repeat_n("null", ORDINARY_MAX_ARRAY_ITEMS)
                    .collect::<Vec<_>>()
                    .join(",")
            )
            .into_bytes(),
            ORDINARY_RESOURCE_PROFILE,
        );
        assert_eq!(at_boundary.status, Status::InvalidSource);
        assert!(at_boundary.processing_complete);
        assert_primary(&at_boundary, CODE_INVALID_DISCRIMINATOR);

        let over = format!(
            "[{}]",
            std::iter::repeat_n("null", ORDINARY_MAX_ARRAY_ITEMS + 1)
                .collect::<Vec<_>>()
                .join(",")
        );
        assert_json_resource_limit(over.as_bytes());
    }

    #[test]
    fn decoded_string_and_key_byte_limits_are_enforced() {
        let string_at_boundary =
            serde_json::to_vec(&string_with_decoded_bytes(ORDINARY_MAX_STRING_BYTES)).unwrap();
        let at_boundary = admit_body_document(&string_at_boundary, ORDINARY_RESOURCE_PROFILE);
        assert_eq!(at_boundary.status, Status::InvalidSource);
        assert!(at_boundary.processing_complete);
        assert_primary(&at_boundary, CODE_INVALID_DISCRIMINATOR);

        let string_over =
            serde_json::to_vec(&string_with_decoded_bytes(ORDINARY_MAX_STRING_BYTES + 1)).unwrap();
        assert_json_resource_limit(&string_over);

        let key_at_boundary = admit_body_document(
            &object_with_key_bytes(ORDINARY_MAX_STRING_BYTES),
            ORDINARY_RESOURCE_PROFILE,
        );
        assert_eq!(key_at_boundary.status, Status::InvalidSource);
        assert!(key_at_boundary.processing_complete);
        assert_primary(&key_at_boundary, CODE_INVALID_DISCRIMINATOR);

        assert_json_resource_limit(&object_with_key_bytes(ORDINARY_MAX_STRING_BYTES + 1));

        let escaped = format!("\"{}\"", "\\n".repeat(ORDINARY_MAX_STRING_BYTES + 1));
        assert_json_resource_limit(escaped.as_bytes());
    }

    #[test]
    fn raw_number_token_limit_has_inclusive_and_oversize_boundaries() {
        let at_boundary = format!("1e{}", "0".repeat(ORDINARY_MAX_NUMBER_TOKEN_BYTES - 2));
        assert_eq!(at_boundary.len(), ORDINARY_MAX_NUMBER_TOKEN_BYTES);
        let result = admit_body_document(
            &source_with_revision_token(&at_boundary),
            ORDINARY_RESOURCE_PROFILE,
        );
        assert_eq!(result.status, Status::Success);

        let over = format!("1e{}", "0".repeat(ORDINARY_MAX_NUMBER_TOKEN_BYTES - 1));
        assert_eq!(over.len(), ORDINARY_MAX_NUMBER_TOKEN_BYTES + 1);
        let result = admit_body_document(
            &source_with_revision_token(&over),
            ORDINARY_RESOURCE_PROFILE,
        );
        assert_eq!(result.status, Status::ResourceLimit);
        assert!(!result.processing_complete);
        assert_primary(&result, CODE_RESOURCE_JSON_WORK);
    }

    #[test]
    fn malformed_numeric_forms_are_invalid_before_resource_scanning() {
        for (name, token) in [
            ("invalid-prefix", "1x"),
            ("leading-zero", "01"),
            ("bad-exponent", "1e+"),
        ] {
            let result = admit_body_document(
                &source_with_revision_token(token),
                ORDINARY_RESOURCE_PROFILE,
            );
            assert_eq!(result.status, Status::InvalidSource, "{name}");
            assert!(result.processing_complete, "{name}");
            assert_primary(&result, CODE_INVALID_JSON);
        }

        let oversized_valid = format!("1e{}", "0".repeat(ORDINARY_MAX_NUMBER_TOKEN_BYTES - 1));
        let result = admit_body_document(
            &source_with_revision_token(&oversized_valid),
            ORDINARY_RESOURCE_PROFILE,
        );
        assert_eq!(result.status, Status::ResourceLimit);
        assert!(!result.processing_complete);
        assert_primary(&result, CODE_RESOURCE_JSON_WORK);
    }

    #[test]
    fn revision_recognition_uses_json_schema_numeric_equality() {
        for token in ["1.0", "1e0", "1E+0", "0.10e1"] {
            let result = admit_body_document(
                &source_with_revision_token(token),
                ORDINARY_RESOURCE_PROFILE,
            );
            assert_eq!(result.status, Status::Success, "revision token {token}");
        }
    }

    #[test]
    fn discriminator_shape_and_types_precede_family_and_revision_recognition() {
        let mut extra_member: Value =
            serde_json::from_slice(&fixture("minimal-valid-envelope")).unwrap();
        let contract = extra_member["contract"].as_object_mut().unwrap();
        contract.insert("extra".to_owned(), Value::Null);
        contract["family"] = Value::String("other.family".to_owned());
        assert_primary(
            &admit_body_document(
                &serde_json::to_vec(&extra_member).unwrap(),
                ORDINARY_RESOURCE_PROFILE,
            ),
            CODE_INVALID_DISCRIMINATOR,
        );

        let mut missing_revision: Value =
            serde_json::from_slice(&fixture("minimal-valid-envelope")).unwrap();
        let contract = missing_revision["contract"].as_object_mut().unwrap();
        contract.remove("revision");
        contract["family"] = Value::String("other.family".to_owned());
        assert_primary(
            &admit_body_document(
                &serde_json::to_vec(&missing_revision).unwrap(),
                ORDINARY_RESOURCE_PROFILE,
            ),
            CODE_INVALID_DISCRIMINATOR,
        );

        let mut malformed_revision: Value =
            serde_json::from_slice(&fixture("minimal-valid-envelope")).unwrap();
        let contract = malformed_revision["contract"].as_object_mut().unwrap();
        contract["family"] = Value::String("other.family".to_owned());
        contract["revision"] = Value::String("1".to_owned());
        assert_primary(
            &admit_body_document(
                &serde_json::to_vec(&malformed_revision).unwrap(),
                ORDINARY_RESOURCE_PROFILE,
            ),
            CODE_INVALID_DISCRIMINATOR,
        );

        let mut unsupported_with_extra: Value =
            serde_json::from_slice(&fixture("minimal-valid-envelope")).unwrap();
        let contract = unsupported_with_extra["contract"].as_object_mut().unwrap();
        contract["revision"] = Value::Number(serde_json::Number::from(2));
        contract.insert("extra".to_owned(), Value::Null);
        assert_primary(
            &admit_body_document(
                &serde_json::to_vec(&unsupported_with_extra).unwrap(),
                ORDINARY_RESOURCE_PROFILE,
            ),
            CODE_INVALID_DISCRIMINATOR,
        );
    }

    #[test]
    fn zero_diagnostic_capacity_still_rejects_schema_errors_and_reserves_primary() {
        let profile = ResourceProfile {
            max_diagnostics: 0,
            ..ORDINARY_RESOURCE_PROFILE
        };
        let result = admit_fixture("unknown-core-member", profile);
        assert_eq!(result.status, Status::InvalidSource);
        assert!(result.processing_complete);
        assert!(!result.diagnostics_complete);
        assert!(result.diagnostics.is_empty());
        assert_eq!(
            result
                .primary_diagnostic
                .as_ref()
                .map(|diagnostic| diagnostic.code),
            Some(CODE_SOURCE_SCHEMA)
        );
        assert!(result.document.is_none());
    }

    #[test]
    fn retention_keeps_reached_entries_and_tracks_normative_primary_independently() {
        let mut accumulator = DiagnosticAccumulator::new(1);
        accumulator.retain(
            DiagnosticKey {
                instance_path: "/z".to_owned(),
                schema_path: "/schema".to_owned(),
                error_kind: "type".to_owned(),
            },
            Diagnostic {
                code: CODE_SOURCE_SCHEMA,
                message: "later reached".to_owned(),
                instance_path: Some("/z".to_owned()),
                schema_path: Some("/schema".to_owned()),
            },
        );
        accumulator.retain(
            DiagnosticKey {
                instance_path: "/a".to_owned(),
                schema_path: "/schema".to_owned(),
                error_kind: "type".to_owned(),
            },
            Diagnostic {
                code: CODE_SOURCE_SCHEMA,
                message: "normatively first".to_owned(),
                instance_path: Some("/a".to_owned()),
                schema_path: Some("/schema".to_owned()),
            },
        );

        let (ordinary, complete, primary) = accumulator.finish().unwrap();
        assert!(!complete);
        assert_eq!(ordinary.len(), 1);
        assert_eq!(ordinary[0].instance_path.as_deref(), Some("/z"));
        assert_eq!(primary.instance_path.as_deref(), Some("/a"));
    }

    #[test]
    fn schema_diagnostics_are_bounded_structural_and_deterministic() {
        let mut value: Value = serde_json::from_slice(&fixture("minimal-valid-envelope")).unwrap();
        value["body"]["parts"] = Value::Array(vec![Value::Null; ORDINARY_MAX_DIAGNOSTICS + 8]);
        let source = serde_json::to_vec(&value).unwrap();
        let result = admit_body_document(&source, ORDINARY_RESOURCE_PROFILE);
        assert_eq!(result.status, Status::InvalidSource);
        assert_eq!(result.diagnostics.len(), ORDINARY_MAX_DIAGNOSTICS);
        assert!(!result.diagnostics_complete);
        assert_eq!(
            result
                .primary_diagnostic
                .as_ref()
                .and_then(|diagnostic| diagnostic.instance_path.as_deref()),
            Some("/body/parts/0")
        );

        let keys: Vec<_> = result
            .diagnostics
            .iter()
            .map(|diagnostic| {
                (
                    diagnostic.instance_path.as_deref().unwrap_or_default(),
                    diagnostic.schema_path.as_deref().unwrap_or_default(),
                )
            })
            .collect();
        assert!(keys.windows(2).all(|window| window[0] <= window[1]));
        assert!(
            result
                .diagnostics
                .iter()
                .all(|diagnostic| diagnostic.code == CODE_SOURCE_SCHEMA)
        );
    }

    #[test]
    fn embedded_schema_is_meta_valid_and_self_contained() {
        validate_embedded_schema().expect("the committed embedded schema must compile");
    }

    #[test]
    fn fixture_manifest_schema_is_draft_2020_12_valid_and_matches_manifest() {
        let schema: Value = serde_json::from_str(include_str!(
            "../../../spec/fixture-manifest/schema/ck-fixture-manifest-v1.schema.json"
        ))
        .unwrap();
        let manifest: Value = serde_json::from_str(include_str!(
            "../../../fixtures/body-documents/readiness-2/manifest.v1.json"
        ))
        .unwrap();
        let validator = jsonschema::draft202012::options().build(&schema).unwrap();
        validator.validate(&manifest).unwrap();
    }

    #[test]
    fn typed_records_preserve_json_numbers() {
        let source = br#"{
          "contract":{"family":"creature-kernel.body","revision":1},
          "source":{"document":"main","namespace":"main","dependencies":[]},
          "basis":{"length_unit":"metre","handedness":"right","up":"+y","forward":"+z"},
          "profiles":{"semantic_numeric":"ck.numeric-frame.r1"},
          "body":{"modules":[],"parts":[{"address":{"namespace":"main","anchors":[],"kind":"part","role":"root"},"containment":{"root":true},"placement":{"translation":[0.1,2,3],"rotation_xyzw":[0,0,0,1]}}],"joints":[],"sockets":[],"attachments":[],"landmarks":[],"dimensions":[],"frames":[],"regions":[],"capabilities":[],"fields":[]},
          "extensions":[]
        }"#;
        let result = admit_body_document(source, ORDINARY_RESOURCE_PROFILE);
        assert_eq!(result.status, Status::Success);
        let number = &result.document.unwrap().body.parts[0].placement.translation[0];
        assert_eq!(number.to_string(), "0.1");
    }

    #[test]
    fn diagnostic_error_selection_is_stable_by_structural_key() {
        let source = br#"{"contract":{"family":"creature-kernel.body","revision":1},"source":{"document":"main","namespace":"main","dependencies":[]},"basis":{"length_unit":"bad","handedness":"right","up":"+y","forward":"+z"},"profiles":{"semantic_numeric":"ck.numeric-frame.r1"},"body":{},"extensions":[]}"#;
        let result = admit_body_document(source, ORDINARY_RESOURCE_PROFILE);
        assert_eq!(result.status, Status::InvalidSource);
        let diagnostic = result.primary_diagnostic.unwrap();
        assert_eq!(diagnostic.code, CODE_SOURCE_SCHEMA);
        assert_eq!(
            diagnostic.instance_path.as_deref(),
            Some("/basis/length_unit")
        );
    }

    #[test]
    fn status_serialization_uses_closed_wire_spellings() {
        assert_eq!(
            serde_json::to_string(&Status::InvalidSource).unwrap(),
            "\"invalid-source\""
        );
        assert_eq!(
            serde_json::to_string(&Status::InternalFailure).unwrap(),
            "\"internal-failure\""
        );
    }

    #[test]
    fn schema_errors_do_not_leak_a_partial_document() {
        let result = admit_fixture("unknown-core-member", ORDINARY_RESOURCE_PROFILE);
        assert_eq!(result.status, Status::InvalidSource);
        assert!(result.document.is_none());
        assert!(result.primary_diagnostic.is_some());
    }
}
