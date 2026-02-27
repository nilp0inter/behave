module Widgets.StringInput exposing (Config, view)

import Html exposing (..)
import Html.Attributes exposing (..)
import Html.Events exposing (onInput)


type alias Config msg =
    { name : String
    , value : String
    , onChange : String -> msg
    }


view : Config msg -> Html msg
view config =
    input
        [ type_ "text"
        , value config.value
        , onInput config.onChange
        , placeholder config.name
        , class "w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
        ]
        []
