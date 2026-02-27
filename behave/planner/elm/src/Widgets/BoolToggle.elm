module Widgets.BoolToggle exposing (Config, view)

import Html exposing (..)
import Html.Attributes exposing (..)
import Html.Events exposing (onClick)


type alias Config msg =
    { name : String
    , value : String
    , onChange : String -> msg
    }


view : Config msg -> Html msg
view config =
    let
        isOn =
            config.value == "true" || config.value == "True" || config.value == "1"

        bgClass =
            if isOn then
                "bg-blue-600"

            else
                "bg-gray-300"

        dotTransform =
            if isOn then
                "translate-x-5"

            else
                "translate-x-0"

        newValue =
            if isOn then
                "false"

            else
                "true"
    in
    div [ class "flex items-center gap-2" ]
        [ button
            [ class ("relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 " ++ bgClass)
            , onClick (config.onChange newValue)
            ]
            [ span
                [ class ("pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out " ++ dotTransform)
                ]
                []
            ]
        , span [ class "text-sm text-gray-600" ]
            [ text
                (if isOn then
                    "true"

                 else
                    "false"
                )
            ]
        ]
