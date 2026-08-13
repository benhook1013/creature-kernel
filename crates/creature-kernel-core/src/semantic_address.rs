//! Provisional structural representation of a body-document semantic address.
//!
//! [`AddressKey`] is deliberately only an identity/index key.  It does not
//! perform Readiness 3 normalization, canonical serialization, digest
//! calculation, or any numeric/frame interpretation.  The semantic-address
//! specification is still Proposed; this module is the small structural slice
//! needed to make the admitted Readiness 2 document inspectable.

use crate::body_document::{Address, AddressKind};
use std::cmp::Ordering;
use std::fmt;
use std::hash::{Hash, Hasher};

/// The closed address-kind rank used by the provisional structural index.
///
/// Keep this separate from wire enum spelling: the wire enum is not an order
/// key.  The ranks mirror the current Proposed semantic-address profile.
#[must_use]
pub const fn kind_rank(kind: &AddressKind) -> u8 {
    match kind {
        AddressKind::Part => 0,
        AddressKind::Joint => 1,
        AddressKind::Socket => 2,
        AddressKind::Attachment => 3,
        AddressKind::Region => 4,
        AddressKind::Capability => 5,
        AddressKind::Field => 6,
    }
}

/// Stable lower-case name for a closed address kind.
#[must_use]
pub const fn kind_name(kind: &AddressKind) -> &'static str {
    match kind {
        AddressKind::Part => "part",
        AddressKind::Joint => "joint",
        AddressKind::Socket => "socket",
        AddressKind::Attachment => "attachment",
        AddressKind::Region => "region",
        AddressKind::Capability => "capability",
        AddressKind::Field => "field",
    }
}

/// Validate one restricted-ASCII identifier component.
#[must_use]
pub fn is_identifier(value: &str) -> bool {
    let mut bytes = value.bytes();
    matches!(bytes.next(), Some(b'a'..=b'z'))
        && bytes.all(|byte| matches!(byte, b'a'..=b'z' | b'0'..=b'9' | b'_'))
}

/// A structural, typed key for a wire [`Address`].
///
/// Equality and ordering are structural: namespace, ordered anchors, frozen
/// kind rank, then role.  Anchor vectors use Rust's lexicographic ordering,
/// which has the required prefix-before-extension behaviour.
#[derive(Clone, Debug)]
pub struct AddressKey {
    namespace: String,
    anchors: Vec<String>,
    kind: AddressKind,
    role: String,
}

impl AddressKey {
    /// Convert and validate one wire address.
    pub fn from_wire(address: &Address) -> Result<Self, AddressKeyError> {
        if !is_identifier(&address.namespace) {
            return Err(AddressKeyError::InvalidComponent {
                component: AddressComponent::Namespace,
                value: address.namespace.clone(),
            });
        }
        for anchor in &address.anchors {
            if !is_identifier(anchor) {
                return Err(AddressKeyError::InvalidComponent {
                    component: AddressComponent::Anchor,
                    value: anchor.clone(),
                });
            }
        }
        if !is_identifier(&address.role) {
            return Err(AddressKeyError::InvalidComponent {
                component: AddressComponent::Role,
                value: address.role.clone(),
            });
        }
        // AddressKind is a closed Rust enum.  Keeping this match explicit is
        // intentional: if the wire vocabulary is ever expanded, this key
        // should fail closed until its rank table is updated.
        let kind = match address.kind {
            AddressKind::Part
            | AddressKind::Joint
            | AddressKind::Socket
            | AddressKind::Attachment
            | AddressKind::Region
            | AddressKind::Capability
            | AddressKind::Field => address.kind.clone(),
        };
        Ok(Self {
            namespace: address.namespace.clone(),
            anchors: address.anchors.clone(),
            kind,
            role: address.role.clone(),
        })
    }

    /// Namespace component.
    #[must_use]
    pub fn namespace(&self) -> &str {
        &self.namespace
    }

    /// Ordered anchor components.
    #[must_use]
    pub fn anchors(&self) -> &[String] {
        &self.anchors
    }

    /// Typed closed kind.
    #[must_use]
    pub fn kind(&self) -> &AddressKind {
        &self.kind
    }

    /// Role component.
    #[must_use]
    pub fn role(&self) -> &str {
        &self.role
    }
}

impl TryFrom<&Address> for AddressKey {
    type Error = AddressKeyError;

    fn try_from(value: &Address) -> Result<Self, Self::Error> {
        Self::from_wire(value)
    }
}

impl TryFrom<Address> for AddressKey {
    type Error = AddressKeyError;

    fn try_from(value: Address) -> Result<Self, Self::Error> {
        Self::from_wire(&value)
    }
}

impl PartialEq for AddressKey {
    fn eq(&self, other: &Self) -> bool {
        self.namespace == other.namespace
            && self.anchors == other.anchors
            && kind_rank(&self.kind) == kind_rank(&other.kind)
            && self.role == other.role
    }
}

impl Eq for AddressKey {}

impl Hash for AddressKey {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.namespace.hash(state);
        self.anchors.hash(state);
        kind_rank(&self.kind).hash(state);
        self.role.hash(state);
    }
}

impl Ord for AddressKey {
    fn cmp(&self, other: &Self) -> Ordering {
        self.namespace
            .cmp(&other.namespace)
            .then_with(|| self.anchors.cmp(&other.anchors))
            .then_with(|| kind_rank(&self.kind).cmp(&kind_rank(&other.kind)))
            .then_with(|| self.role.cmp(&other.role))
    }
}

impl PartialOrd for AddressKey {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl fmt::Display for AddressKey {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{}:{:?}:{}:{}",
            self.namespace(),
            self.anchors(),
            kind_name(self.kind()),
            self.role()
        )
    }
}

/// Component that failed the restricted identifier profile.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum AddressComponent {
    Namespace,
    Anchor,
    Role,
}

/// Address conversion failure.  Unknown kinds cannot currently be produced
/// by the closed wire enum, but the conversion remains explicitly fail-closed.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum AddressKeyError {
    InvalidComponent {
        component: AddressComponent,
        value: String,
    },
}

impl fmt::Display for AddressKeyError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidComponent { component, value } => {
                write!(formatter, "invalid {component:?} identifier {value:?}")
            }
        }
    }
}

impl std::error::Error for AddressKeyError {}

#[cfg(test)]
mod tests {
    use super::*;

    fn address(namespace: &str, anchors: &[&str], kind: AddressKind, role: &str) -> Address {
        Address {
            namespace: namespace.to_owned(),
            anchors: anchors.iter().map(|anchor| (*anchor).to_owned()).collect(),
            kind,
            role: role.to_owned(),
        }
    }

    #[test]
    fn address_order_is_structural_and_prefix_first() {
        let short = AddressKey::try_from(&address("n", &["a"], AddressKind::Part, "z")).unwrap();
        let long =
            AddressKey::try_from(&address("n", &["a", "b"], AddressKind::Part, "a")).unwrap();
        let joint = AddressKey::try_from(&address("n", &["a"], AddressKind::Joint, "a")).unwrap();
        assert!(short < long);
        assert!(short < joint);
    }

    #[test]
    fn malformed_components_are_rejected() {
        let invalid = address("Bad", &[], AddressKind::Part, "root");
        assert!(matches!(
            AddressKey::try_from(&invalid),
            Err(AddressKeyError::InvalidComponent { .. })
        ));
    }

    #[test]
    fn identifier_boundaries_are_closed_and_ascii_only() {
        for valid in ["a", "a0", "a_", "z9_name"] {
            assert!(is_identifier(valid), "expected valid identifier {valid:?}");
        }
        for invalid in ["", "0a", "_a", "A", "a-", "a.b", "é"] {
            assert!(
                !is_identifier(invalid),
                "expected invalid identifier {invalid:?}"
            );
        }
    }

    #[test]
    fn all_closed_kind_ranks_have_the_frozen_order() {
        let kinds = [
            AddressKind::Part,
            AddressKind::Joint,
            AddressKind::Socket,
            AddressKind::Attachment,
            AddressKind::Region,
            AddressKind::Capability,
            AddressKind::Field,
        ];
        let keys: Vec<_> = kinds
            .iter()
            .map(|kind| AddressKey::try_from(&address("n", &[], kind.clone(), "r")).unwrap())
            .collect();
        assert!(keys.windows(2).all(|pair| pair[0] < pair[1]));
        assert_eq!(
            kinds.iter().map(kind_rank).collect::<Vec<_>>(),
            vec![0, 1, 2, 3, 4, 5, 6]
        );
    }
}
