module ParamEditor exposing (view)

import Html exposing (..)
import Html.Attributes exposing (..)
import Types exposing (..)
import Widgets.BoolToggle as BoolToggle
import Widgets.EnumSelect as EnumSelect
import Widgets.FloatSlider as FloatSlider
import Widgets.IntInput as IntInput
import Widgets.StringInput as StringInput


type alias Config msg =
    { onUpdate : String -> String -> msg
    }


view : Config msg -> List ParamDefData -> Maybe PlanParams -> Html msg
view config paramDefs planParams =
    div [ class "mt-2 ml-6 p-3 bg-gray-50 rounded-lg border border-gray-200 space-y-3" ]
        (List.map (viewParam config planParams) paramDefs)


viewParam : Config msg -> Maybe PlanParams -> ParamDefData -> Html msg
viewParam config planParams paramDef =
    let
        currentValue =
            planParams
                |> Maybe.andThen (findParamValue paramDef.name)
                |> Maybe.withDefault ""

        widget =
            case paramDef.choices of
                Just choices ->
                    EnumSelect.view
                        { name = paramDef.name
                        , choices = choices
                        , value = currentValue
                        , onChange = config.onUpdate paramDef.name
                        }

                Nothing ->
                    case paramDef.paramType of
                        "float" ->
                            FloatSlider.view
                                { name = paramDef.name
                                , min = paramDef.min
                                , max = paramDef.max
                                , value = currentValue
                                , onChange = config.onUpdate paramDef.name
                                }

                        "int" ->
                            IntInput.view
                                { name = paramDef.name
                                , min = paramDef.min
                                , max = paramDef.max
                                , value = currentValue
                                , onChange = config.onUpdate paramDef.name
                                }

                        "str" ->
                            StringInput.view
                                { name = paramDef.name
                                , value = currentValue
                                , onChange = config.onUpdate paramDef.name
                                }

                        "bool" ->
                            BoolToggle.view
                                { name = paramDef.name
                                , value = currentValue
                                , onChange = config.onUpdate paramDef.name
                                }

                        _ ->
                            StringInput.view
                                { name = paramDef.name
                                , value = currentValue
                                , onChange = config.onUpdate paramDef.name
                                }
    in
    div [ class "flex items-center gap-3" ]
        [ label [ class "text-sm font-mono text-gray-600 w-36 flex-shrink-0" ]
            [ text paramDef.name ]
        , div [ class "flex-1" ] [ widget ]
        , viewConstraints paramDef
        ]


viewConstraints : ParamDefData -> Html msg
viewConstraints paramDef =
    let
        parts =
            List.filterMap identity
                [ Maybe.map (\m -> "min: " ++ String.fromFloat m) paramDef.min
                , Maybe.map (\m -> "max: " ++ String.fromFloat m) paramDef.max
                , Maybe.map (\c -> String.fromInt (List.length c) ++ " choices") paramDef.choices
                ]
    in
    if List.isEmpty parts then
        text ""

    else
        span [ class "text-xs text-gray-400 flex-shrink-0" ]
            [ text (String.join " | " parts) ]


findParamValue : String -> PlanParams -> Maybe String
findParamValue name params =
    params
        |> List.filterMap
            (\( k, v ) ->
                if k == name then
                    Just (planValueToString v)

                else
                    Nothing
            )
        |> List.head
