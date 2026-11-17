let
    Source = Csv.Document(File.Contents("C:\Users\nandi\Downloads\shap_importance.csv"),[Delimiter=",", Columns=6, Encoding=1252, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{"Rank", Int64.Type}, {"Feature", type text}, {"MeanAbsoluteSHAP", type number}, {"MeanSHAP", type number}, {"ExplainedOutput", type text}, {"SampleSize", Int64.Type}})
in
    #"Changed Type"