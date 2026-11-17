let
    Source = Csv.Document(File.Contents("C:\Users\nandi\Downloads\shap_local_explanations.csv"),[Delimiter=",", Columns=11, Encoding=1252, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{"row_index", Int64.Type}, {"actual_class", type text}, {"predicted_class", type text}, {"predicted_class_probability", type number}, {"probability_satisfied", type number}, {"correct_prediction", type logical}, {"feature", type text}, {"feature_value", type text}, {"shap_value", type number}, {"direction", type text}, {"rank_by_absolute_contribution", Int64.Type}})
in
    #"Changed Type"