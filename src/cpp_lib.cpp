#include <stdint.h>
#include <math.h>
extern "C" {
    bool can_buy(const double* amounts, const double* costs, const int32_t* allowed_purchases, int max_dims, int line) {
        int amounts_features = max_dims + 2;
        int costs_features = max_dims + 1;
        int allowed_purchases_features = max_dims + 1;
        return (costs[line * costs_features + allowed_purchases[line * allowed_purchases_features + 0]] <= amounts[line * amounts_features + 0]);
    }

    bool can_buy_all(const double* amounts, const double* costs, const int32_t* allowed_purchases, int num_objects, int max_dims, bool* marked) {
        bool found = false;
        #pragma omp parallel for
        for (int line = 0; line < num_objects; ++line) {
            if (can_buy(amounts, costs, allowed_purchases, max_dims, line)) {
                marked[line] = true;
                #pragma omp atomic write
                found = true;
            }
        }
        return found;
    }


    double sacrifice_multiplier(double sacrificed_amount) {
        if (sacrificed_amount == 0) {
            return 1;
        } else {
            return pow(fmax(log10(sacrificed_amount)/10, 1), 2);
        }
    }

    double predict_sacrifice_boost(const double* amounts, int max_dims, int line) {
        int amounts_features = max_dims + 2;
        double old_sacrificed_amount = amounts[line * amounts_features + max_dims + 1];
        double old_sacrifice_multiplier = sacrifice_multiplier(old_sacrificed_amount);
        double new_sacrificed_amount = old_sacrificed_amount + amounts[line * amounts_features + 1];
        double new_sacrifice_multiplier = sacrifice_multiplier(new_sacrificed_amount);
        return new_sacrifice_multiplier / old_sacrifice_multiplier;
    }

    double can_sacrifice(const double* amounts, const float* allowed_sacrifices, int max_dims, int sacrifices_length, int line) {
        int amounts_features = max_dims + 2;
        if (amounts[line * amounts_features + 8] == 0) {
            return 0;
        }
        double sacrifice_boost = predict_sacrifice_boost(amounts, max_dims, line);
        if (sacrifice_boost >= allowed_sacrifices[line * sacrifices_length + 0]) {
            return sacrifice_boost;
        } else {
            return 0;
        }
    }

    bool can_sacrifice_all(const double* amounts, const float* allowed_sacrifices, int num_objects, int max_dims, int sacrifices_length, double* sacrifice_boosts) {
        bool found = false;
        #pragma omp parallel for
        for (int line = 0; line < num_objects; ++line) {
            double sacrifice_boost = can_sacrifice(amounts, allowed_sacrifices, max_dims, sacrifices_length, line);
            if (sacrifice_boost > 0) {
                sacrifice_boosts[line] = sacrifice_boost;
                #pragma omp atomic write
                found = true;
            }
        }
        return found;
    }


    // does i dominates over j
    bool dominates(const double* amounts, const int32_t* bought_amounts, int max_dims, int i, int j) {
        int amounts_features = max_dims + 2;
        for (int k = 0; k < amounts_features; ++k) {
            double val_first_i = amounts[i * amounts_features + k];
            double val_first_j = amounts[j * amounts_features + k];
            if (val_first_i < val_first_j) return false;
        }
        int bought_amounts_features = max_dims + 1;
        for (int k = 0; k < bought_amounts_features; ++k) {
            int32_t val_second_i = bought_amounts[i * bought_amounts_features + k];
            int32_t val_second_j = bought_amounts[j * bought_amounts_features + k];
            if (val_second_i < val_second_j) return false;
        }
        return true;
    }

    void find_dominated(const double* amounts, const int32_t* bought_amounts, const int32_t* sorted_indices, int num_objects, int max_dims, bool* marked) {
        #pragma omp parallel for
        for (int j = 1; j < num_objects; ++j) {
            for (int i = 0; i < j; ++i) {
                if ((not marked[sorted_indices[i]]) and (dominates(amounts, bought_amounts, max_dims, sorted_indices[i], sorted_indices[j]))) {
                    marked[sorted_indices[j]] = true;
                    break;
                }
            }
        }
    }
}