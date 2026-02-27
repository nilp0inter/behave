module FeatureTree exposing (view)

import Html exposing (..)
import Html.Attributes exposing (..)
import Html.Events exposing (onClick)
import Types exposing (..)


view : Maybe String -> List FeatureTreeNode -> (String -> msg) -> Html msg
view selectedPath nodes onSelect =
    div [ class "h-full overflow-y-auto" ]
        [ div [ class "p-4" ]
            [ h2 [ class "text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3" ]
                [ text "Features" ]
            , div [] (List.map (viewNode selectedPath onSelect 0) nodes)
            ]
        ]


viewNode : Maybe String -> (String -> msg) -> Int -> FeatureTreeNode -> Html msg
viewNode selectedPath onSelect depth node =
    case treeNodeType node of
        DirectoryNode ->
            div []
                [ div
                    [ class "flex items-center py-1.5 px-2 text-sm text-gray-600"
                    , style "padding-left" (String.fromInt (depth * 16) ++ "px")
                    ]
                    [ span [ class "mr-1.5 text-gray-400" ] [ text "+" ]
                    , span [ class "font-medium" ] [ text (treeNodeName node) ]
                    ]
                , div [] (List.map (viewNode selectedPath onSelect (depth + 1)) (treeNodeChildren node))
                ]

        FileNode ->
            let
                isSelected =
                    selectedPath == Just (treeNodePath node)

                bgClass =
                    if isSelected then
                        "bg-blue-50 text-blue-700 border-r-2 border-blue-600"

                    else
                        "text-gray-700 hover:bg-gray-50"
            in
            div
                [ class ("flex items-center py-1.5 px-2 text-sm cursor-pointer rounded-l " ++ bgClass)
                , style "padding-left" (String.fromInt (depth * 16 + 4) ++ "px")
                , onClick (onSelect (treeNodePath node))
                ]
                [ span [ class "mr-1.5 text-gray-400" ] [ text "~" ]
                , span [] [ text (treeNodeName node) ]
                ]
