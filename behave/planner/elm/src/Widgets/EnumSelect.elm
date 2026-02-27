module Widgets.EnumSelect exposing (Config, view)

import Html exposing (..)
import Html.Attributes exposing (..)
import Html.Events exposing (onInput)


type alias Config msg =
    { name : String
    , choices : List String
    , value : String
    , onChange : String -> msg
    }


view : Config msg -> Html msg
view config =
    select
        [ value config.value
        , onInput config.onChange
        , class "px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono bg-white"
        ]
        (option [ value "", disabled True, selected (config.value == "") ] [ text ("Select " ++ config.name ++ "...") ]
            :: List.map
                (\choice ->
                    option
                        [ value choice
                        , selected (config.value == choice)
                        ]
                        [ text choice ]
                )
                config.choices
        )
