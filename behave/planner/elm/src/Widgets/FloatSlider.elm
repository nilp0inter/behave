module Widgets.FloatSlider exposing (Config, view)

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
    let
        minVal =
            Maybe.withDefault 0 config.min

        maxVal =
            Maybe.withDefault 100 config.max

        stepVal =
            (maxVal - minVal) / 100
    in
    div [ class "flex items-center gap-2" ]
        [ input
            [ type_ "range"
            , Html.Attributes.min (String.fromFloat minVal)
            , Html.Attributes.max (String.fromFloat maxVal)
            , step (String.fromFloat stepVal)
            , value config.value
            , onInput config.onChange
            , class "flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            ]
            []
        , input
            [ type_ "number"
            , Html.Attributes.min (String.fromFloat minVal)
            , Html.Attributes.max (String.fromFloat maxVal)
            , step (String.fromFloat stepVal)
            , value config.value
            , onInput config.onChange
            , class "w-20 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
            ]
            []
        ]
