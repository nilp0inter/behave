module Api exposing (fetchFeatureTree, fetchFeatureDetail, fetchPlan, updateParam)

import Http
import Json.Encode as E
import Types exposing (..)
import Url


fetchFeatureTree : (Result Http.Error (List FeatureTreeNode) -> msg) -> Cmd msg
fetchFeatureTree toMsg =
    Http.get
        { url = "/api/features"
        , expect = Http.expectJson toMsg featureTreeDecoder
        }


fetchFeatureDetail : String -> (Result Http.Error FeatureDetail -> msg) -> Cmd msg
fetchFeatureDetail path toMsg =
    Http.get
        { url = "/api/features/" ++ path
        , expect = Http.expectJson toMsg featureDetailDecoder
        }


fetchPlan : String -> (Result Http.Error PlanResponse -> msg) -> Cmd msg
fetchPlan path toMsg =
    Http.get
        { url = "/api/plans/" ++ path
        , expect = Http.expectJson toMsg planResponseDecoder
        }


updateParam :
    { featurePath : String
    , scenario : String
    , stepIdx : Int
    , paramName : String
    , value : E.Value
    }
    -> (Result Http.Error UpdateResponse -> msg)
    -> Cmd msg
updateParam params toMsg =
    let
        url =
            "/api/params/"
                ++ params.featurePath
                ++ "/"
                ++ Url.percentEncode params.scenario
                ++ "/"
                ++ String.fromInt params.stepIdx
                ++ "/"
                ++ Url.percentEncode params.paramName
    in
    Http.request
        { method = "PUT"
        , headers = []
        , url = url
        , body = Http.jsonBody (E.object [ ( "value", params.value ) ])
        , expect = Http.expectJson toMsg updateResponseDecoder
        , timeout = Nothing
        , tracker = Nothing
        }
