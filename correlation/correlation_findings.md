# Correlation Analysis Findings

## 1. Overview

Correlation analysis was performed to identify associations between passenger characteristics, flight attributes, service ratings and overall airline passenger satisfaction.

The cleaned dataset contained 129,487 records. The target variable was encoded as:

- Satisfied: 1
- Neutral or Dissatisfied: 0

Different statistical measures were selected according to feature type:

- Point-biserial correlation for numerical features against binary satisfaction.
- Spearman correlation for ordinal service ratings against binary satisfaction.
- Cramér's V for categorical features against binary satisfaction.

Benjamini-Hochberg correction was applied to account for multiple statistical tests.

## 2. Categorical Feature Associations

Cramér's V was used to measure associations between categorical passenger attributes and satisfaction.

| Feature | Cramér's V |
|---|---:|
| Class | 0.50346 |
| Type of Travel | 0.44979 |
| Customer Type | 0.18591 |
| Gender | 0.01116 |

Class showed the strongest categorical association with passenger satisfaction, followed by Type of Travel. Customer Type showed a comparatively smaller association, while Gender had a negligible association.

Cramér's V measures association strength and does not indicate whether a feature is positively or negatively associated with satisfaction.

## 3. Numerical Feature Associations

Point-biserial correlation was used to examine relationships between numerical attributes and binary satisfaction.

| Feature | Point-Biserial Correlation |
|---|---:|
| Flight Distance | +0.29821 |
| Age | +0.13400 |
| Arrival Delay | -0.05828 |
| Departure Delay | -0.05103 |

Flight Distance showed the strongest numerical association with satisfaction, followed by Age. Departure Delay and Arrival Delay showed weak negative associations, indicating that higher delays were associated with slightly lower satisfaction in the dataset.

The delay correlations were comparatively small and should not be interpreted as strong relationships.

## 4. Ordinal Service Rating Associations

Spearman correlation was used to examine monotonic relationships between ordinal service ratings and passenger satisfaction.

The strongest positive associations were:

| Feature | Spearman Correlation |
|---|---:|
| Online Boarding | +0.58971 |
| In-flight Entertainment | +0.39973 |
| In-flight Wi-Fi Service | +0.37213 |
| Seat Comfort | +0.36128 |
| On-board Service | +0.32847 |
| Leg Room Service | +0.31902 |
| Cleanliness | +0.30509 |
| Baggage Handling | +0.27056 |
| In-flight Service | +0.26566 |
| Check-in Service | +0.23345 |
| Ease of Online Booking | +0.23144 |
| Food and Drink | +0.20868 |

Online Boarding had the strongest ordinal association with satisfaction. In-flight Entertainment, Wi-Fi Service and Seat Comfort also showed notable positive associations.

Departure and Arrival Time Convenience showed a weak negative association (-0.04873), while Gate Location showed an association close to zero (-0.00362). Gate Location was not statistically significant (p = 0.192).

## 5. Passenger Segment-Wise Correlation Findings

Correlation analysis was also performed separately across passenger segments to explore whether satisfaction-related associations varied between groups.

Some notable observations included:

- **Travel Class:** Online Boarding was strongly associated with satisfaction among Business-class passengers (0.5715). In Economy and Economy Plus, In-flight Wi-Fi Service showed notable associations (0.5822 and 0.6373, respectively).
- **Customer Type:** In-flight Wi-Fi Service and Ease of Online Booking showed relatively strong associations among first-time passengers (0.6493 and 0.6133). Online Boarding showed a strong association among returning passengers (0.5679).
- **Type of Travel:** Online Boarding showed a strong association among business-travel passengers (0.6399), while In-flight Wi-Fi Service and Ease of Online Booking were among the stronger associations for personal-travel passengers (0.4621 and 0.4175).

These findings suggest that the service attributes associated with satisfaction differ across passenger segments. However, the subgroup correlations are descriptive; no formal statistical test was performed to establish whether the correlation coefficients differ significantly between groups.

## 6. Interpretation and Key Observations

The correlation analysis highlights several important patterns:

1. Online Boarding has the strongest ordinal association with passenger satisfaction.
2. Class and Type of Travel are the strongest categorical associations.
3. Flight Distance has the strongest numerical association with satisfaction.
4. Flight delays have comparatively weak negative associations.
5. Gender has a negligible categorical association with satisfaction.
6. The strongest service-related associations vary across passenger segments.

The findings indicate that service experience and travel characteristics are associated with passenger satisfaction in different ways. These associations provide a foundation for subsequent predictive modelling and explainability analysis.

## 7. Statistical Considerations and Limitations

Correlation measures identify statistical associations and do not establish causation. The coefficients from Point-Biserial, Spearman and Cramér's V are not directly interchangeable because they measure different types of relationships.

Zero-valued service ratings were treated as not applicable rather than as the lowest rating. These values were excluded from the corresponding pairwise statistical calculations while the passenger records were retained.

Very small p-values may appear as 0.0 due to numerical precision. Such values should be reported as p < 0.001 rather than interpreted as exactly zero.

The segment-wise analysis provides descriptive comparisons. Further statistical testing would be required to establish whether differences between subgroup correlations are statistically significant.

## 8. Conclusion

The analysis identifies Online Boarding, In-flight Entertainment, In-flight Wi-Fi Service and Seat Comfort as important service-related features associated with passenger satisfaction. Class and Type of Travel also demonstrate notable categorical associations.

These results complement the predictive modelling stage by providing statistical evidence about relationships in the dataset. They also provide a basis for interpreting model-based feature importance and generating actionable insights through explainable AI.

## 9. Comparison Between Correlation Analysis and Logistic Regression

The statistical association results were compared with the coefficients obtained from the Logistic Regression model to examine whether the relationships identified through correlation analysis were also reflected in predictive modelling.

Online Boarding exhibited the strongest Spearman association with passenger satisfaction (0.58971) and also had a positive Logistic Regression coefficient of 1.13666. Similarly, In-flight Wi-Fi Service showed a positive Spearman correlation of 0.37213 and a positive Logistic Regression coefficient of 1.07098.

These consistent positive directions indicate that service attributes associated with satisfaction in the bivariate statistical analysis also contributed positively to the Logistic Regression model's predictions.

For categorical attributes, Class and Type of Travel showed relatively strong associations with satisfaction, with Cramér's V values of 0.50346 and 0.44979, respectively. The Logistic Regression coefficients also indicated different contributions for their encoded categories. Business Travel had a positive coefficient of 1.21970, whereas Personal Travel had a negative coefficient of -2.11947.

Some differences were also observed. Gender showed a negligible Cramér's V value of 0.01116, whereas the encoded Gender coefficient was non-zero. This illustrates that bivariate association measures and multivariable model coefficients capture different relationships. Correlation analysis evaluates an individual feature's association with the target, whereas Logistic Regression estimates conditional relationships while considering the other predictors.

A particularly notable result was the coefficient of +8.59049 for the In-flight Wi-Fi Not Applicable indicator. Further investigation found that 3,908 passengers had Wi-Fi ratings marked as not applicable, of whom 99.74% were satisfied. Among these passengers, several other service attributes were also frequently marked as not applicable. This indicates a strong dataset-specific pattern associated with service-rating applicability. It should not be interpreted as evidence that unavailable Wi-Fi causes higher satisfaction.

The comparison demonstrates that correlation analysis and Logistic Regression provide complementary perspectives. Correlation measures identify individual feature associations, whereas Logistic Regression captures conditional relationships within a predictive model. Their numerical values are not directly interchangeable because the features undergo different transformations and the measures represent different statistical quantities.

Overall, Online Boarding and In-flight Wi-Fi Service showed consistent positive relationships across the statistical and Logistic Regression analyses. Further comparison with SHAP-based feature importance can help determine whether these patterns are also reflected in the selected ensemble model.

