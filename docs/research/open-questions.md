# Open research questions

Status: Active registry

Questions are grouped by domain. IDs are stable and should be referenced by
experiments, decision records, fixtures, and benchmarks.

## Product proof

| ID | Question | State |
| --- | --- | --- |
| RQ-001 | What smallest result proves that unified body generation is valuable? | Open |
| RQ-002 | What visual quality makes a generated form read as an intentional stylized creature character rather than an articulated blob? | Open |
| RQ-003 | Which body variation range is useful before support becomes bespoke? | Open |
| RQ-004 | When, if ever, can model-assisted visual analysis provide reliable, actionable feedback on creature defects without displacing human visual judgment? | Open |

## Body grammar and semantics

| ID | Question | State |
| --- | --- | --- |
| RQ-010 | What is the first supported morphology family? | Open |
| RQ-011 | Which primitives and attachment rules express that family? | Open |
| RQ-012 | How are semantic fields, local coordinates, and part identity represented through composition? | Open |
| RQ-013 | Which assemblies are invalid, ambiguous, or physically impossible? | Open |
| RQ-014 | How are plantigrade, digitigrade, quadruped, tail, wing, and extra-limb structures related or separated? | Deferred |

## Surface and topology

| ID | Question | State |
| --- | --- | --- |
| RQ-020 | Should the initial surface use signed-distance fields, skeleton-radius meshing, patches, or a hybrid? | Open |
| RQ-021 | Can the method produce useful shoulders, hips, mouths, paws, and branch junctions without a base mesh? | Open |
| RQ-022 | Is generated triangle topology sufficient for the first animation proof? | Open |
| RQ-023 | When is remeshing or retopology required, and can it preserve semantic fields? | Open |
| RQ-024 | How are sharp, thin, hollow, or separate features represented? | Open |

## Rigging, animation, and control

| ID | Question | State |
| --- | --- | --- |
| RQ-030 | How are skinning weights generated and validated from body fields? | Open |
| RQ-031 | What joint corrections are necessary for acceptable stylized deformation? | Open |
| RQ-032 | What first animation or procedural control scenario should all generated bodies share? | Open |
| RQ-033 | How should locomotion adapt across proportions and later morphology families? | Deferred |
| RQ-034 | How are balance, support, gait, and physical animation coordinated? | Deferred |

## Contact and deformation

| ID | Question | State |
| --- | --- | --- |
| RQ-040 | Which representation owns collision after visible surface deformation? | Open |
| RQ-041 | Which localized effects need bones, morphs, cages, fields, or volumetric simulation? | Open |
| RQ-042 | How are IK, collision, balance, and physical response conflicts resolved? | Open |
| RQ-043 | How much two-way regional soft-body interaction fits a high-end real-time budget? | Open |
| RQ-044 | How are volume preservation, maximum strain, recovery, and style expressed consistently? | Open |
| RQ-045 | Can radial opening and local bulge deformation use generic semantic regions without bespoke per-character work? | Open |

## Compilation and runtime

| ID | Question | State |
| --- | --- | --- |
| RQ-050 | Which operations compile once, run asynchronously, or remain active at runtime? | Open |
| RQ-051 | Which body changes preserve topology and runtime state? | Open |
| RQ-052 | How does an avatar-package swap preserve animation, attachments, collision, and saves? | Deferred |
| RQ-053 | What frame target, resolution, hardware, and active-character count define success? | Open |
| RQ-054 | What minimum fallback remains useful without advanced GPU deformation? | Open |
| RQ-055 | What determinism is required for saving, replay, or networking? | Open |

## Technology and integration

| ID | Question | State |
| --- | --- | --- |
| RQ-060 | Which language and build system best support the compiler and runtime boundary? | Open |
| RQ-061 | Which geometry library or host tool should power the first surface experiment? | Open |
| RQ-062 | Which game engine should receive the first adapter? | Partially answered — qualified: the bounded Godot 4.7.2 feasibility trial is complete, but no permanent host or adapter is selected. A later comparison can refresh Bevy 0.19 using first-party BRP and separately qualified community MCP, agent, and physics tooling. See [first host runtime evaluation](first-host-runtime-evaluation.md). |
| RQ-063 | Which collision, compute, and deformable-body backends should be evaluated? | Open |
| RQ-064 | What serialized format and compatibility model should the runtime avatar use? | Open |
| RQ-065 | How are large generated artifacts stored and reproduced? | Open |

## External assets and creative systems

| ID | Question | State |
| --- | --- | --- |
| RQ-070 | What minimum metadata lets an external mesh join the semantic body model? | Deferred |
| RQ-071 | How reliably can arbitrary topology bind to generated cages or fields? | Deferred |
| RQ-072 | How are faces, eyes, mouths, paws, claws, teeth, horns, and ears generated? | Open |
| RQ-073 | How do clothing, hair, and fur bind to regenerated bodies? | Deferred |
| RQ-074 | How much technical-art knowledge must be encoded in generators and presets? | Open |
