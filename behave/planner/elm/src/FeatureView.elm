module FeatureView exposing (view)

import Html exposing (..)
import Html.Attributes exposing (..)
import Html.Events exposing (onClick)
import ParamEditor
import Set exposing (Set)
import Types exposing (..)


type alias Config msg =
    { expandedSteps : Set String
    , onToggleStep : String -> msg
    , onParamUpdate : String -> Int -> String -> String -> msg
    , featurePath : String
    , planData : Maybe PlanData
    }


view : Config msg -> FeatureDetail -> Html msg
view config feature =
    div [ class "p-6 max-w-4xl" ]
        [ viewFeatureHeader feature
        , viewBackground config feature.background
        , div [] (List.map (viewScenario config) feature.scenarios)
        , div [] (List.map (viewRule config) feature.rules)
        ]


viewFeatureHeader : FeatureDetail -> Html msg
viewFeatureHeader feature =
    div [ class "mb-6" ]
        [ div [ class "flex items-center gap-2 mb-1" ]
            [ span [ class "text-blue-600 font-bold text-lg" ] [ text "Feature:" ]
            , span [ class "text-lg font-semibold text-gray-800" ] [ text feature.name ]
            ]
        , if not (List.isEmpty feature.tags) then
            div [ class "flex gap-1 mt-1" ]
                (List.map viewTag feature.tags)

          else
            text ""
        , if not (List.isEmpty feature.description) then
            div [ class "mt-2 text-sm text-gray-600 ml-4" ]
                (List.map (\line -> p [ class "mb-0.5" ] [ text line ]) feature.description)

          else
            text ""
        ]


viewBackground : Config msg -> Maybe BackgroundData -> Html msg
viewBackground config maybeBg =
    case maybeBg of
        Nothing ->
            text ""

        Just bg ->
            div [ class "mb-4" ]
                [ div [ class "flex items-center gap-2 mb-2" ]
                    [ span [ class "text-purple-600 font-semibold" ] [ text "Background:" ]
                    ]
                , div [ class "ml-4 space-y-1" ]
                    (List.map (viewStep config "Background") bg.steps)
                ]


viewScenario : Config msg -> ScenarioData -> Html msg
viewScenario config scenario =
    div [ class "mb-6" ]
        [ div [ class "flex items-center gap-2 mb-2" ]
            [ span [ class "text-green-700 font-semibold" ] [ text "Scenario:" ]
            , span [ class "font-medium text-gray-800" ] [ text scenario.name ]
            ]
        , if not (List.isEmpty scenario.tags) then
            div [ class "flex gap-1 mb-2 ml-4" ]
                (List.map viewTag scenario.tags)

          else
            text ""
        , div [ class "ml-4 space-y-1" ]
            (List.map (viewStep config scenario.name) scenario.steps)
        ]


viewRule : Config msg -> RuleData -> Html msg
viewRule config rule =
    div [ class "mb-6 ml-2 pl-4 border-l-2 border-gray-200" ]
        [ div [ class "flex items-center gap-2 mb-2" ]
            [ span [ class "text-orange-600 font-semibold" ] [ text "Rule:" ]
            , span [ class "font-medium text-gray-800" ] [ text rule.name ]
            ]
        , div [] (List.map (viewScenario config) rule.scenarios)
        ]


viewStep : Config msg -> String -> StepData -> Html msg
viewStep config scenarioName step =
    let
        stepKey =
            scenarioName ++ "/" ++ String.fromInt step.index

        isExpanded =
            Set.member stepKey config.expandedSteps

        planParams =
            getPlanParams config.planData scenarioName step.index
    in
    div [ class "py-0.5" ]
        [ div [ class "flex items-baseline gap-1 group" ]
            [ span [ class (keywordClass step.keyword ++ " font-semibold flex-shrink-0") ]
                [ text step.keyword ]
            , span [ class "text-gray-800" ] [ text step.name ]
            , if step.hasParams then
                button
                    [ class "ml-1 px-1.5 py-0.5 text-xs rounded border border-gray-300 text-gray-500 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-600 transition-colors flex-shrink-0"
                    , onClick (config.onToggleStep stepKey)
                    ]
                    [ text
                        (if isExpanded then
                            "[-]"

                         else
                            "[+]"
                        )
                    ]

              else
                text ""
            ]
        , if step.hasParams && isExpanded then
            ParamEditor.view
                { onUpdate = config.onParamUpdate scenarioName step.index
                }
                step.params
                planParams

          else
            text ""
        ]


viewTag : String -> Html msg
viewTag tag =
    span [ class "inline-block px-2 py-0.5 text-xs rounded-full bg-yellow-100 text-yellow-800 border border-yellow-200" ]
        [ text ("@" ++ tag) ]


keywordClass : String -> String
keywordClass kw =
    case kw of
        "Given" ->
            "text-blue-600"

        "When" ->
            "text-green-600"

        "Then" ->
            "text-red-600"

        "And" ->
            "text-gray-500"

        "But" ->
            "text-gray-500"

        _ ->
            "text-gray-600"


getPlanParams : Maybe PlanData -> String -> Int -> Maybe PlanParams
getPlanParams maybePlan scenarioName stepIdx =
    maybePlan
        |> Maybe.andThen
            (\plan ->
                plan.scenarios
                    |> List.filter (\s -> s.scenario == scenarioName)
                    |> List.head
            )
        |> Maybe.andThen
            (\scenario ->
                scenario.steps
                    |> List.indexedMap Tuple.pair
                    |> List.filter (\( i, _ ) -> i == stepIdx)
                    |> List.head
                    |> Maybe.map Tuple.second
            )
        |> Maybe.andThen .params
