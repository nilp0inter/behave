module Main exposing (main)

import Api
import Browser
import FeatureTree
import FeatureView
import Html exposing (..)
import Html.Attributes exposing (..)
import Http
import Json.Encode as E
import Set exposing (Set)
import Types exposing (..)


main : Program () Model Msg
main =
    Browser.element
        { init = init
        , update = update
        , view = view
        , subscriptions = \_ -> Sub.none
        }



-- MODEL


type alias Model =
    { featureTree : List FeatureTreeNode
    , selectedFeaturePath : Maybe String
    , featureDetail : Maybe FeatureDetail
    , planData : Maybe PlanData
    , expandedSteps : Set String
    , error : Maybe String
    , saveStatus : SaveStatus
    }


type SaveStatus
    = Idle
    | Saving
    | SaveOk
    | SaveError String


init : () -> ( Model, Cmd Msg )
init _ =
    ( { featureTree = []
      , selectedFeaturePath = Nothing
      , featureDetail = Nothing
      , planData = Nothing
      , expandedSteps = Set.empty
      , error = Nothing
      , saveStatus = Idle
      }
    , Api.fetchFeatureTree GotFeatureTree
    )



-- MSG


type Msg
    = GotFeatureTree (Result Http.Error (List FeatureTreeNode))
    | SelectFeature String
    | GotFeatureDetail (Result Http.Error FeatureDetail)
    | GotPlan (Result Http.Error PlanResponse)
    | ToggleStep String
    | UpdateParam String Int String String
    | GotUpdateResponse (Result Http.Error UpdateResponse)



-- UPDATE


update : Msg -> Model -> ( Model, Cmd Msg )
update msg model =
    case msg of
        GotFeatureTree result ->
            case result of
                Ok tree ->
                    ( { model | featureTree = tree, error = Nothing }, Cmd.none )

                Err err ->
                    ( { model | error = Just (httpErrorToString err) }, Cmd.none )

        SelectFeature path ->
            ( { model
                | selectedFeaturePath = Just path
                , featureDetail = Nothing
                , planData = Nothing
                , expandedSteps = Set.empty
                , error = Nothing
                , saveStatus = Idle
              }
            , Cmd.batch
                [ Api.fetchFeatureDetail path GotFeatureDetail
                , Api.fetchPlan path GotPlan
                ]
            )

        GotFeatureDetail result ->
            case result of
                Ok detail ->
                    ( { model | featureDetail = Just detail, error = Nothing }, Cmd.none )

                Err err ->
                    ( { model | error = Just (httpErrorToString err) }, Cmd.none )

        GotPlan result ->
            case result of
                Ok response ->
                    ( { model | planData = response.data, error = Nothing }, Cmd.none )

                Err err ->
                    ( { model | error = Just (httpErrorToString err) }, Cmd.none )

        ToggleStep key ->
            let
                newExpanded =
                    if Set.member key model.expandedSteps then
                        Set.remove key model.expandedSteps

                    else
                        Set.insert key model.expandedSteps
            in
            ( { model | expandedSteps = newExpanded }, Cmd.none )

        UpdateParam scenarioName stepIdx paramName rawValue ->
            case model.selectedFeaturePath of
                Nothing ->
                    ( model, Cmd.none )

                Just featurePath ->
                    let
                        jsonValue =
                            parseValue rawValue
                    in
                    ( { model | saveStatus = Saving }
                    , Api.updateParam
                        { featurePath = featurePath
                        , scenario = scenarioName
                        , stepIdx = stepIdx
                        , paramName = paramName
                        , value = jsonValue
                        }
                        GotUpdateResponse
                    )

        GotUpdateResponse result ->
            case result of
                Ok response ->
                    if response.status == "ok" then
                        case model.selectedFeaturePath of
                            Just path ->
                                ( { model | saveStatus = SaveOk }, Api.fetchPlan path GotPlan )

                            Nothing ->
                                ( { model | saveStatus = SaveOk }, Cmd.none )

                    else
                        ( { model | saveStatus = SaveError (Maybe.withDefault "Unknown error" response.message) }, Cmd.none )

                Err err ->
                    ( { model | saveStatus = SaveError (httpErrorToString err) }, Cmd.none )


parseValue : String -> E.Value
parseValue raw =
    case String.toFloat raw of
        Just f ->
            if String.contains "." raw then
                E.float f

            else
                case String.toInt raw of
                    Just i ->
                        E.int i

                    Nothing ->
                        E.float f

        Nothing ->
            case raw of
                "true" ->
                    E.bool True

                "false" ->
                    E.bool False

                _ ->
                    E.string raw



-- VIEW


view : Model -> Html Msg
view model =
    div [ class "flex h-screen bg-white" ]
        [ -- Sidebar
          div [ class "w-64 border-r border-gray-200 bg-gray-50 flex-shrink-0" ]
            [ div [ class "p-4 border-b border-gray-200" ]
                [ h1 [ class "text-lg font-bold text-gray-800" ] [ text "behave planner" ]
                ]
            , FeatureTree.view model.selectedFeaturePath model.featureTree SelectFeature
            ]

        -- Main panel
        , div [ class "flex-1 overflow-y-auto" ]
            [ viewStatusBar model
            , viewMainContent model
            ]
        ]


viewStatusBar : Model -> Html Msg
viewStatusBar model =
    let
        statusContent =
            case model.saveStatus of
                Idle ->
                    []

                Saving ->
                    [ span [ class "text-blue-600" ] [ text "Saving..." ] ]

                SaveOk ->
                    [ span [ class "text-green-600" ] [ text "Saved" ] ]

                SaveError msg ->
                    [ span [ class "text-red-600" ] [ text ("Error: " ++ msg) ] ]

        errorContent =
            case model.error of
                Just err ->
                    [ span [ class "text-red-600" ] [ text err ] ]

                Nothing ->
                    []

        allContent =
            statusContent ++ errorContent
    in
    if List.isEmpty allContent then
        text ""

    else
        div [ class "px-6 py-2 bg-gray-50 border-b border-gray-200 text-sm" ]
            allContent


viewMainContent : Model -> Html Msg
viewMainContent model =
    case model.featureDetail of
        Nothing ->
            div [ class "flex items-center justify-center h-full text-gray-400" ]
                [ div [ class "text-center" ]
                    [ p [ class "text-lg mb-2" ] [ text "Select a feature file" ]
                    , p [ class "text-sm" ] [ text "Choose a .feature file from the sidebar to view and configure parameters" ]
                    ]
                ]

        Just feature ->
            FeatureView.view
                { expandedSteps = model.expandedSteps
                , onToggleStep = ToggleStep
                , onParamUpdate = UpdateParam
                , featurePath = Maybe.withDefault "" model.selectedFeaturePath
                , planData = model.planData
                }
                feature


httpErrorToString : Http.Error -> String
httpErrorToString err =
    case err of
        Http.BadUrl url ->
            "Bad URL: " ++ url

        Http.Timeout ->
            "Request timed out"

        Http.NetworkError ->
            "Network error"

        Http.BadStatus status ->
            "Server error: " ++ String.fromInt status

        Http.BadBody body ->
            "Bad response: " ++ body
