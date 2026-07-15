# specs/ — frozen work-unit contracts

One contract per work unit, `NNN_<slug>_spec.md` (the spec, plan, and record of one
work unit share the number — see `development/policies/naming_conventions.md`). A
spec is frozen at acceptance: what to build, the interfaces later work units import,
and the acceptance criteria; template in
`development/policies/document_kinds.md` §2. Changing a frozen interface is a
trunk decision, never a local edit.
