# specs/ — frozen step/feature contracts

One contract per work unit, `SXX_<snake>.md` (the spec, plan, and record of one work
unit share the ID — see `development/policies/naming_conventions.md`). A spec is
frozen at acceptance: what to build, the interfaces later steps import, and the
acceptance criteria; template in `development/policies/records_and_liveness.md` §2.
Changing a frozen interface is a trunk decision, never a local edit.
