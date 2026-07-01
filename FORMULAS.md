# Schedule Cost Formula

For person `p`, assigned roles are `R_p`. Each role `i` has weight `w_i` and time index `t_i`.

## 1. Preference

`preference_p = sum(w_i * unwanted_coefficient_p,i)`

`preference_cost_p = lambda_preference * preference_p`

Penalizes unwanted assignments; an unspecified coefficient is zero.

## 2. Actual and Expected Load

`actual_load_p = sum(w_i)`

`expected_load_p = total_schedule_load * portion_p / sum(all portions)`

Measures assigned burden and the person's fair capacity-based share.

## 3. Historical Load Fairness

`current_ratio_p = actual_load_p / expected_load_p`

`effective_ratio_p = recency * current_ratio_p + (1 - recency) * historical_ratio_p`

Blends the current load ratio with the historical moving ratio.

`load_cost_p = lambda_load * abs(effective_ratio_p - 1)`

Penalizes underload and overload equally.

## 4. Internal Distribution

`internal_p = sum((w_i * w_j) / abs(t_i - t_j)^2), for every pair i < j`

Penalizes nearby assignments, especially when both are heavy.

## 5. Previous-Schedule Boundary

`boundary_p = (first_weight * previous_final_weight) / abs(first_time - previous_final_time)^2`

Penalizes a heavy first assignment too close to the previous schedule's final assignment.

## 6. Distribution Cost

`distribution_cost_p = lambda_distribution * (internal_p + boundary_p) / actual_load_p`

Measures how concentrated the person's assigned load is.

## 7. Final Cost

`person_cost_p = preference_cost_p + distribution_cost_p + load_cost_p`

`global_cost = sum(person_cost_p for all people)`

The scheduler minimizes the additive global cost.

Current values: `lambda_distribution = 8`, `lambda_load = 36`, `recency = 0.6`.
