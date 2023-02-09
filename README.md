# OPA_policy_list_action

### Simon Duff
### https://linkedin.com/in/sduff

Parse a list of policies and summarise the results.

Policy list file should be in the same format at Terraform Cloud's `policies.hcl` format.

```
policy "policy.rego" {
  query = "data.deny"
  enforcement_level = "mandatory"
}

policy "another_policy.rego" {
  query = "data.deny"
  enforcement_level = "advisory"
}
```
