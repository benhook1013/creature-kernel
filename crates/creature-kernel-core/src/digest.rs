//! Preparatory, crate-private domain-separated SHA-256 framing.
//!
//! This primitive deliberately does not select any production identity domain,
//! profile, canonical representation, or `content_sha256` interpretation. A
//! caller supplies both profile components explicitly, and the payload is
//! treated as opaque bytes. Readiness activation and every public digest or
//! serialization contract remain outside this module.

#![allow(dead_code)]

use core::fmt;

use sha2::{Digest as Sha2Digest, Sha256};

const FRAME_PREFIX: &[u8] = b"creature-kernel";
const NUL: u8 = 0;
const DIGEST_LENGTH: usize = 32;

/// The caller-supplied component that failed profile validation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum DigestProfileComponent {
    DomainTag,
    ProfileId,
}

/// Why one caller-supplied profile component is invalid.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum DigestProfileErrorReason {
    Empty,
    NonAscii,
    ContainsNul,
}

/// A typed profile validation error identifying both component and reason.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct DigestProfileError {
    component: DigestProfileComponent,
    reason: DigestProfileErrorReason,
}

impl DigestProfileError {
    pub(crate) const fn component(self) -> DigestProfileComponent {
        self.component
    }

    pub(crate) const fn reason(self) -> DigestProfileErrorReason {
        self.reason
    }
}

impl fmt::Display for DigestProfileError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        let component = match self.component {
            DigestProfileComponent::DomainTag => "domain tag",
            DigestProfileComponent::ProfileId => "profile id",
        };
        let reason = match self.reason {
            DigestProfileErrorReason::Empty => "must not be empty",
            DigestProfileErrorReason::NonAscii => "must contain only ASCII bytes",
            DigestProfileErrorReason::ContainsNul => "must not contain NUL",
        };
        write!(formatter, "digest profile {component} {reason}")
    }
}

impl std::error::Error for DigestProfileError {}

/// An explicit caller-supplied framing profile.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct DigestProfile<'a> {
    domain_tag: &'a str,
    profile_id: &'a str,
}

impl<'a> DigestProfile<'a> {
    /// Validates and constructs a profile without selecting production
    /// domain/profile values.
    pub(crate) fn new(
        domain_tag: &'a str,
        profile_id: &'a str,
    ) -> Result<Self, DigestProfileError> {
        validate_component(domain_tag, DigestProfileComponent::DomainTag)?;
        validate_component(profile_id, DigestProfileComponent::ProfileId)?;
        Ok(Self {
            domain_tag,
            profile_id,
        })
    }
}

fn validate_component(
    value: &str,
    component: DigestProfileComponent,
) -> Result<(), DigestProfileError> {
    if value.is_empty() {
        return Err(DigestProfileError {
            component,
            reason: DigestProfileErrorReason::Empty,
        });
    }
    if value.as_bytes().contains(&NUL) {
        return Err(DigestProfileError {
            component,
            reason: DigestProfileErrorReason::ContainsNul,
        });
    }
    if !value.is_ascii() {
        return Err(DigestProfileError {
            component,
            reason: DigestProfileErrorReason::NonAscii,
        });
    }
    Ok(())
}

/// The exact 32-byte SHA-256 result, kept behind a crate-private typed carrier.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub(crate) struct FramedDigest([u8; DIGEST_LENGTH]);

impl FramedDigest {
    /// Returns the digest bytes for another crate-private computation or test.
    pub(crate) const fn as_bytes(&self) -> &[u8; DIGEST_LENGTH] {
        &self.0
    }
}

/// Hashes the exact framed preimage:
/// `creature-kernel`, NUL, domain tag, NUL, profile id, NUL, payload.
pub(crate) fn framed_sha256(profile: &DigestProfile<'_>, payload: &[u8]) -> FramedDigest {
    let mut hasher = Sha256::new();
    hasher.update(FRAME_PREFIX);
    hasher.update([NUL]);
    hasher.update(profile.domain_tag.as_bytes());
    hasher.update([NUL]);
    hasher.update(profile.profile_id.as_bytes());
    hasher.update([NUL]);
    hasher.update(payload);
    FramedDigest(hasher.finalize().into())
}

#[cfg(test)]
mod tests {
    use super::{DigestProfile, DigestProfileComponent, DigestProfileErrorReason, framed_sha256};

    #[test]
    fn complete_framed_preimage_matches_independent_known_vector() {
        let profile = DigestProfile::new("test-domain", "profile-1").unwrap();

        // Independent `sha256sum` vector for:
        // printf 'creature-kernel\0test-domain\0profile-1\0payload' | sha256sum
        let expected = [
            0x6a, 0x80, 0xc3, 0x1f, 0xca, 0xa7, 0x3b, 0xfd, 0xa2, 0xa3, 0x5b, 0xe7, 0x14, 0x93,
            0xa4, 0x95, 0xf4, 0x30, 0x4b, 0x96, 0x49, 0xfa, 0xc9, 0xa4, 0xb9, 0x2d, 0x19, 0xd0,
            0xa0, 0x62, 0x84, 0xfa,
        ];

        assert_eq!(framed_sha256(&profile, b"payload").as_bytes(), &expected);
    }

    #[test]
    fn repeated_hashing_is_deterministic() {
        let profile = DigestProfile::new("domain", "profile").unwrap();
        let first = framed_sha256(&profile, b"same payload");
        let second = framed_sha256(&profile, b"same payload");

        assert_eq!(first, second);
    }

    #[test]
    fn domain_and_profile_components_are_separated() {
        let base = DigestProfile::new("domain", "profile").unwrap();
        let other_domain = DigestProfile::new("other-domain", "profile").unwrap();
        let other_profile = DigestProfile::new("domain", "other-profile").unwrap();

        let base_digest = framed_sha256(&base, b"payload");
        assert_ne!(base_digest, framed_sha256(&other_domain, b"payload"));
        assert_ne!(base_digest, framed_sha256(&other_profile, b"payload"));
    }

    #[test]
    fn payload_is_opaque_including_empty_binary_nul_and_sha256_text() {
        let profile = DigestProfile::new("domain", "profile").unwrap();
        let empty = framed_sha256(&profile, b"");
        let binary = framed_sha256(&profile, b"\0\x01\xffsha256:literal\0");

        assert_ne!(empty, binary);
        assert_eq!(empty.as_bytes().len(), 32);
        assert_eq!(binary.as_bytes().len(), 32);
    }

    #[test]
    fn invalid_profile_components_report_component_and_reason() {
        let cases = [
            (
                "",
                "profile",
                DigestProfileComponent::DomainTag,
                DigestProfileErrorReason::Empty,
            ),
            (
                "domain",
                "",
                DigestProfileComponent::ProfileId,
                DigestProfileErrorReason::Empty,
            ),
            (
                "d\u{80}main",
                "profile",
                DigestProfileComponent::DomainTag,
                DigestProfileErrorReason::NonAscii,
            ),
            (
                "domain",
                "pro\u{80}file",
                DigestProfileComponent::ProfileId,
                DigestProfileErrorReason::NonAscii,
            ),
            (
                "do\0main",
                "profile",
                DigestProfileComponent::DomainTag,
                DigestProfileErrorReason::ContainsNul,
            ),
            (
                "domain",
                "pro\0file",
                DigestProfileComponent::ProfileId,
                DigestProfileErrorReason::ContainsNul,
            ),
        ];

        for (domain_tag, profile_id, component, reason) in cases {
            let error = DigestProfile::new(domain_tag, profile_id).unwrap_err();
            assert_eq!(error.component(), component);
            assert_eq!(error.reason(), reason);
        }
    }
}
