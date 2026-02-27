module Widgets.IntInput exposing (Config, view)

import Html exposing (..)
import Html.Attributes exposing (..)
import Html.Events exposing (onInput)


type alias Config msg =
    { name : String
    , min : Maybe Float
    , max : Maybe Float
    , value : String
    , onChange : String -> msg
    }


view : Config msg -> Html msg
view config =
    input
        [ type_ "number"
        , step "1"
        , value config.value
        , onInput config.onChange
        , Maybe.withDefault (class "") (Maybe.map (\m -> Html.Attributes.min (String.fromFloat m)) config.min)
        , Maybe.withDefault (class "") (Maybe.map (\m -> Html.Attributes.max (String.fromFloat m)) config.max)
        , class "w-32 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
        ]
        []
