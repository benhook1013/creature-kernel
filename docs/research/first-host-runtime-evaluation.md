# First host runtime evaluation

Status: Research record — provisional candidate, incomplete evidence
Date: 2026-08-25
Question: [RQ-062](open-questions.md#technology-and-integration)

## Scope and disposition

This record captures the current official-source comparison of Godot 4.7.2,
Unity 6.3 LTS, Unreal Engine 5.8, and Bevy 0.19 for the first downstream
runtime-host feasibility work. It is research evidence, not a product,
specification, architecture, or technology-selection decision.

Ben approved Godot 4.7.2 only as the **provisional first reference-host
feasibility candidate**. That approval does not select a permanent engine or
activate an adapter, runtime-avatar package format, solver, or Stage 3. RQ-062
therefore remains open and qualified pending a bounded trial.

The current recommendation is to test Godot first because it offers the
highest information for the lowest lock-in and local setup burden among the
compared hosts. That is a trial-order recommendation, not a claim that Godot
will be the final host.

## Evidence language

- **Fact:** capability, version, license, or requirement stated by the linked
  official primary source.
- **Inference:** a CK assessment drawn from those facts; it is not a measured
  project result.
- **Unknown:** a question that the official documentation does not settle for
  CK's generated avatars, package boundary, contact representation, or
  deformation workload.
- **Trial-required evidence:** a claim that must be demonstrated with a bounded
  CK fixture, declared host configuration, measurements, or rendered output.

No host was installed, built, or run for this record. No performance or visual
claim is made.

## Comparison at 2026-08-25

| Candidate | Official facts relevant to CK | CK inference | Why it is or is not first |
| --- | --- | --- | --- |
| **Godot 4.7.2** | 4.7.2 is the current stable release. Godot is MIT-licensed with separate third-party notices. It provides headless command-line workflows, GDExtension native shared-library loading, `Skeleton3D`, physics contact state, procedural mesh APIs, profiling, and OpenXR support. Rust is not an official scripting-language binding; native C ABI or a community binding would need to be pinned. | Strong low-friction fit for testing a CK-owned package and a replaceable native adapter. The host supplies scene/render/physics machinery without requiring CK to adopt a proprietary engine contract. Rust ABI, mesh/deformation cost, and render/collision coherence remain unproven. | **First provisional candidate.** It is capable enough to exercise the real boundary, open enough to preserve distribution flexibility, and light enough to trial before committing to a larger host. |
| **Unity 6.3 LTS** | Unity 6.3 LTS has dedicated support through December 2027. Unity documents Windows/Linux editor support, native plugins with C-compatible entry points, skinned meshes, command-line builds, profiling, and an OpenXR package. Use and distribution remain governed by Unity's current terms and plan/account model. | Technically credible and possibly a stronger conventional character-rendering baseline. Native Rust-through-C-ABI integration is plausible, but editor/toolchain, terms, account, and supported-host constraints add integration cost that is not needed for the first neutral feasibility probe. | **Not first, but a credible comparison host.** Revisit if Godot's deformation, package-loading, or profiling evidence fails or if Unity's conventional workflow offers a materially better result for a declared CK requirement. |
| **Unreal Engine 5.8** | UE 5.8 is an official release and the last planned major UE5 release on Epic's current roadmap. Epic documents skeletal animation, modular C++ plugins, physics, command-line tooling, profiling, and OpenXR. Epic's EULA governs the engine and its distribution; the documented recommended development configuration includes 32 GB RAM and 8 GB graphics RAM. | It has the deepest built-in route to advanced character, physics, and deformation experiments, but it can make a successful result depend on proprietary engine facilities and brings the largest setup, build, and licensing/distribution burden. | **Not first.** It is a credible later host if the trial needs its higher-end facilities, but it is a poor first test of a portable CK boundary on the current machine and would make attribution of CK versus host capability harder. |
| **Bevy 0.19** | Bevy is a Rust engine under MIT or Apache-2.0. The official 0.19 release documents scene, rendering, and skinned-mesh improvements. The official repository warns that Bevy remains early-stage, important features are missing, documentation is sparse, and breaking releases occur approximately every three months. | Best Rust continuity and low language-boundary friction, but the first trial would also be evaluating or assembling more of the host/editor/physics stack. That risks testing CK's ability to build a game engine rather than testing CK's runtime package boundary. | **Not first, but a meaningful alternative.** Keep it as a fallback or later Rust-native comparison if host ABI friction becomes the dominant Godot problem. |

### Why Godot has the highest information per unit of lock-in

The first trial needs to answer whether CK can compile or provide a
host-neutral runtime representation, load it through a narrow boundary, map a
semantic pose and generated proxies, observe contact, and drive a bounded
deformation/response loop. Godot has enough ordinary engine machinery to make
those questions concrete, while its permissive license and self-contained
release model reduce the cost of discarding the adapter if the evidence is
poor. The comparison does not establish that Godot's soft-body or deformation
systems are the eventual solution.

The alternatives are not rejected. Unity is a strong conventional baseline;
Unreal is a strong high-end capability baseline; Bevy is a strong Rust-
continuity baseline. They are deferred as first hosts because each introduces
a larger confounding factor for this particular first experiment: vendor
terms and editor/tooling, heavy proprietary runtime facilities and hardware
burden, or additional host infrastructure that CK would have to assemble.

## Preserved CK boundary

The host evaluation must not invert the existing architecture direction:

```text
authoritative CK source
  -> CK semantic resolution and validation
  -> CK-owned geometry/rig/skin/proxy compilers
  -> proposed engine-neutral runtime-avatar package
  -> thin host adapter
  -> host scene, rendering, physics, and platform integration
```

The intended division is:

- **Creature Kernel / Rust:** authoritative semantic source, graph resolution,
  stable semantic identity, geometry and embodiment derivation, skeleton and
  skin data, collision-proxy intent, capability metadata, diagnostics,
  package contents, and any CK-owned contact-to-region/deformation policy that
  the later evidence assigns to CK.
- **Thin adapter:** explicit coordinate/unit conversion, package loading,
  semantic-ID mapping, host object creation, proxy updates, host-contact
  translation, capability negotiation, and failure mapping. Host objects and
  IDs must not become CK semantic truth.
- **Evaluated host:** scene and resource lifetime, mesh/skeleton upload,
  skinning, rendering, physics stepping and low-level contact queries, optional
  compute/deformation facilities, profiling, display, export, and future
  platform/XR integration.

The exact ownership of contact resolution, deformation state, physical response,
timing, interpolation, substeps, and CPU/GPU execution remains unresolved.
Those are trial questions, not permissions for the host to redefine CK
semantics.

The post-Readiness-3 gate remains intact. DR-0013 requires a separate
Ben-approved Readiness 3 transaction before resolver/semantic activation and
requires a future adapter to declare its basis map, positive unit scale,
precision, narrowing/overflow/underflow policy, supported domain, and guarantee
tier. Adapter activation remains separate and after Readiness 3. This record
does not create a schema, fixture, package, adapter, or implementation.

## Bounded feasibility trial

The later trial should be titled **Godot 4.7.2 provisional reference-host
feasibility trial**, not “Godot host selection.” It must follow the queued
CK-KICK-016 through CK-KICK-019 prerequisites and use a deliberately narrow
scenario.

The smallest useful candidate scenario is two independently addressed,
substantially different generated avatars undergoing a bounded press-and-
release interaction at a declared semantic region. It should test contact
onset, absence of unacceptable tunnelling or penetration, local response,
recovery, and at least one lower-quality fallback. Tangential sliding,
sustained bracing, cross-profile breadth, and more advanced internal or
regional effects remain later probes unless the first evidence makes them
necessary.

The trial must fail closed or remain explicitly incomplete unless it records:

1. the exact CK package/input provenance and an unchanged host load for each
   avatar package;
2. two distinct generated avatar identities, not two copies of one fixture;
3. a host-neutral semantic pose/target payload, with coordinate conversion
   recorded rather than a host-only animation clip;
4. the tick order, fixed rate, substeps, interpolation policy, and ownership of
   pose, proxies, physics, contact mapping, deformation, and rendering;
5. semantic contact identity, position, normal, impulse/force, enter/exit,
   tick IDs, mapping revision, and rejected or missing-contact diagnostics;
6. a declared physical state change, not only a visual vertex displacement;
7. localized deformation measurements covering onset, peak, recovery, residual
   error, and unwanted regional spread;
8. render/collision coherence at neutral, contact, peak, and recovery states;
9. a CPU-capable baseline, with any GPU path measured separately and a clean
   fallback when unavailable;
10. a declared hardware, OS, driver, renderer, resolution, frame target, and
    budget, with suitable percentile timing and memory measurements; and
11. a rendered capture plus structured telemetry, so subjective visual judgment
    and machine evidence remain distinct.

Passing this bounded trial could support a later host-selection proposal.
Failure would be useful evidence about the package, adapter, solver split, or
the need to compare Unity, Unreal, Bevy, or a different host boundary. Neither
outcome alone accepts a decision record or proves the unbounded Stage 3
roadmap.

## Open unknowns

- Whether the current Readiness 2 outputs can be transformed into the eventual
  engine-neutral package without prematurely freezing its format.
- Whether Rust-to-Godot should use a low-level GDExtension C ABI or a pinned
  community binding, and how lifecycle, ownership, panic, and version rules
  should be handled.
- Whether host collision proxies, an undeformed surface, a deformed surface,
  or another representation should be authoritative for contact.
- Whether local response belongs primarily to CK, the host, or a replaceable
  split, and how to keep render and collision state coherent.
- Whether the WSL2/Linux environment or a native Windows host is the primary
  performance envelope for the first rendered trial.
- What frame target, active-character count, visual bar, quality tiers, and
  fallback are sufficient for the bounded Stage 3 claim.
- Whether Godot's current APIs and version policy remain suitable when the
  actual package and solver prerequisites are ready.

## Official primary sources

The following are direct official sources consulted for this 2026-08-25
comparison. They establish documented capabilities and terms only; they do not
establish CK suitability.

### Godot

- [Godot 4.7.2 stable release](https://godotengine.org/download/archive/4.7.2-stable/)
- [Godot license](https://godotengine.org/license/)
- [Command-line tutorial](https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html)
- [GDExtension system](https://docs.godotengine.org/en/stable/engine_details/engine_api/gdextension/index.html)
- [Skeleton3D](https://docs.godotengine.org/en/stable/classes/class_skeleton3d.html)
- [PhysicsDirectBodyState3D](https://docs.godotengine.org/en/stable/classes/class_physicsdirectbodystate3d.html)
- [Procedural geometry](https://docs.godotengine.org/en/stable/tutorials/3d/procedural_geometry/index.html)
- [Debugger and profiler](https://docs.godotengine.org/en/stable/tutorials/scripting/debug/debugger_panel.html)
- [OpenXR setup](https://docs.godotengine.org/en/stable/tutorials/xr/setting_up_xr.html)
- [Other languages](https://docs.godotengine.org/en/stable/tutorials/scripting/other_languages.html)

### Unity

- [Unity 6.3 LTS announcement](https://unity.com/blog/unity-6-3-lts-is-now-available)
- [Unity 6 support schedule](https://unity.com/releases/unity-6/support)
- [Unity 6 system requirements](https://docs.unity3d.com/6000.0/Documentation/Manual/system-requirements.html)
- [Native plug-ins](https://docs.unity3d.com/6000.0/Documentation/Manual/plug-ins-native.html)
- [Skinned Mesh Renderer](https://docs.unity3d.com/6000.0/Documentation/Manual/class-SkinnedMeshRenderer.html)
- [Command-line builds](https://docs.unity3d.com/6000.0/Documentation/Manual/build-command-line.html)
- [Profiler Highlights](https://docs.unity3d.com/6000.0/Documentation/Manual/ProfilerHighlights.html)
- [Unity OpenXR plug-in](https://docs.unity3d.com/Packages/com.unity.xr.openxr@1.14/manual/index.html)
- [Unity Editor terms](https://unity.com/legal/editor-terms-of-service/software)

### Unreal Engine

- [Unreal Engine 5.8 release](https://www.unrealengine.com/news/unreal-engine-5-8-is-now-available)
- [Hardware and software specifications](https://dev.epicgames.com/documentation/en-us/unreal-engine/hardware-and-software-specifications-for-unreal-engine)
- [Unreal Engine EULA](https://www.unrealengine.com/eula/unreal)
- [Unreal Engine modules](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-modules)
- [Skeletal Mesh Animation System](https://dev.epicgames.com/documentation/en-us/unreal-engine/skeletal-mesh-animation-system-in-unreal-engine)
- [Physics in Unreal Engine](https://dev.epicgames.com/documentation/en-us/unreal-engine/physics-in-unreal-engine)
- [Command-line arguments reference](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-command-line-arguments-reference)
- [Performance profiling](https://dev.epicgames.com/documentation/en-us/unreal-engine/introduction-to-performance-profiling-and-configuration-in-unreal-engine)
- [OpenXR input](https://dev.epicgames.com/documentation/en-us/unreal-engine/openxr-input-in-unreal-engine)

### Bevy

- [Bevy 0.19 release](https://bevy.org/news/bevy-0-19/)
- [Bevy official introduction](https://bevy.org/learn/quick-start/introduction/)
- [Bevy official repository and development-status notice](https://github.com/bevyengine/bevy)
