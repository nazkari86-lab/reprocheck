# Results, Storyline, Findings, and Conclusions for ML Papers

## Goal
Teach students how to:
- build a clear results storyline,
- support claims with evidence,
- present tables and figures well,
- synthesize results into findings,
- write brief, evidence-based conclusions.

---

# 1. What is the Results section for?

The Results section is where the paper makes its empirical case.

It should show:
1. what was observed,
2. whether the evidence supports the claims,
3. how strong and reliable the effect is,
4. what the limits are.

A good Results section is not a list of numbers. It is a structured argument.

---

# 2. Results vs findings vs conclusions

| Part | Main question | Typical content |
|---|---|---|
| Results | What did we observe? | tables, figures, quantitative patterns |
| Findings / Discussion | What do these results mean? | interpretation, mechanism, implications |
| Conclusion | What should the reader remember? | brief take-home message, contribution, limits, next step |

## Teaching rule
**Results = evidence**  
**Findings = interpretation**  
**Conclusion = final takeaway**

---

# 3. Organize results around claims

Do not organize the section by the order in which experiments were run.

Instead, organize it by the paper’s claims.

| Claim | Evidence |
|---|---|
| Our method performs better | main benchmark table |
| Our method is more stable | learning curves / variance plot |
| Component X matters | ablation table |
| The method scales | performance vs agents / graph size |
| The method is robust | perturbation or OOD test |

---

# 4. A good ML results storyline

A simple order that works well:

1. **Headline result** — does the method work on the main task?
2. **Breadth** — does it work across settings?
3. **Explanation** — what do ablations show?
4. **Reliability** — what do seeds, variance, robustness show?
5. **Limits** — where does it fail or weaken?

This gives the section a narrative instead of a data dump.

---

# 5. How to write a results paragraph

A good results paragraph usually has four moves:

1. point to the figure or table,
2. state the main pattern,
3. interpret it,
4. qualify it if needed.

## Template
> **Table/Figure X** shows that **[main pattern]**.  
> Compared with **[baseline]**, **[method]** improves **[metric]** by **[amount]**.  
> This suggests that **[interpretation]**.  
> The effect is strongest in **[condition]**, but weaker in **[condition]**.

---

# 6. Tables vs figures

## Use tables when
- exact values matter,
- several methods must be compared precisely,
- the reader needs to inspect benchmark results.

## Use figures when
- trends matter,
- learning dynamics matter,
- uncertainty or distributions matter,
- the shape of the effect is important.

## Typical ML pairing
- table: final benchmark comparison,
- figure: learning curves,
- table: ablations,
- figure: robustness or scaling trend.

---

# 7. Report uncertainty honestly

Good ML results should usually report:
- multiple random seeds,
- mean and standard deviation or confidence interval,
- instability when relevant.

Do not report only the best run.

---

# 8. From results to findings

A **result** is an observed outcome.  
A **finding** is a broader conclusion supported by several results.

## Example
### Result
> Communication improves return by 8–12% in large networks.

### Finding
> Communication is most useful in large, congested settings where decentralized agents strongly affect one another.

## Synthesis template
> Taken together, the results indicate that **[main finding]**.  
> This is supported by **[main result 1]**, **[main result 2]**, and **[main result 3]**.  
> The effect is strongest under **[condition]** and weaker under **[condition]**.

---

# 9. From findings to conclusions

A **conclusion** is not a repetition of all results.  
It is a short final statement of:
- what the paper showed,
- why it matters,
- what its main limitation is,
- what comes next if needed.

## Good conclusion structure
1. Restate the problem or goal
2. State the main finding
3. State the contribution or implication
4. Briefly note a limitation or future direction

## Template
> This paper studied **[problem]** and showed that **[main finding]**.  
> These results suggest that **[implication or contribution]**.  
> However, the study is limited by **[main limitation]**.  
> Future work should examine **[next step]**.

## Example
> This paper studied decentralized route choice in mixed traffic and showed that communication-aware policies improve both travel time and training stability in larger congested networks. These results suggest that lightweight coordination can substantially strengthen decentralized routing under non-stationarity. However, the evaluation remains limited to simulated environments. Future work should test whether the same pattern holds under richer behavioral models and real-world traffic data.

---

# 10. Common mistakes

| Mistake | Why it is weak |
|---|---|
| Too many tables, no story | reader cannot tell what matters |
| Reporting only best runs | hides variance |
| Reading numbers row by row | no synthesis |
| Hiding weak cases | reduces trust |
| Overclaiming in conclusions | conclusions exceed evidence |
| Conclusion just repeats the abstract | no synthesis or final insight |

---

# 11. Fast checklist

- [ ] My Results section is organized around claims
- [ ] The headline result appears early
- [ ] Each figure or table supports one clear point
- [ ] My text interprets patterns, not just numbers
- [ ] I report uncertainty where needed
- [ ] I mention weak or limiting cases honestly
- [ ] My findings are broader than single results, but still evidence-based
- [ ] My conclusion states the takeaway, contribution, and limit in a few sentences

---

# 12. In-class exercise

Fill in:

## Main claim
> Our paper claims that ...

## Headline result
> The main evidence is shown in ...

## Main finding
> Taken together, the results indicate that ...

## Conclusion
> This paper shows that ...  
> This matters because ...  
> A limitation is ...  
> Next, we should ...
