module Types exposing (..)

import Json.Decode as D


-- FEATURE TREE


type FeatureTreeNode
    = FeatureTreeNode
        { nodeType : NodeType
        , name : String
        , path : String
        , children : List FeatureTreeNode
        }


type NodeType
    = FileNode
    | DirectoryNode


treeNodeType : FeatureTreeNode -> NodeType
treeNodeType (FeatureTreeNode n) =
    n.nodeType


treeNodeName : FeatureTreeNode -> String
treeNodeName (FeatureTreeNode n) =
    n.name


treeNodePath : FeatureTreeNode -> String
treeNodePath (FeatureTreeNode n) =
    n.path


treeNodeChildren : FeatureTreeNode -> List FeatureTreeNode
treeNodeChildren (FeatureTreeNode n) =
    n.children


featureTreeDecoder : D.Decoder (List FeatureTreeNode)
featureTreeDecoder =
    D.field "tree" (D.list featureTreeNodeDecoder)


featureTreeNodeDecoder : D.Decoder FeatureTreeNode
featureTreeNodeDecoder =
    D.map4 (\nt nm p c -> FeatureTreeNode { nodeType = nt, name = nm, path = p, children = c })
        (D.field "type" nodeTypeDecoder)
        (D.field "name" D.string)
        (D.field "path" D.string)
        (D.oneOf
            [ D.field "children" (D.list (D.lazy (\_ -> featureTreeNodeDecoder)))
            , D.succeed []
            ]
        )


nodeTypeDecoder : D.Decoder NodeType
nodeTypeDecoder =
    D.string
        |> D.andThen
            (\s ->
                case s of
                    "file" ->
                        D.succeed FileNode

                    "directory" ->
                        D.succeed DirectoryNode

                    _ ->
                        D.fail ("Unknown node type: " ++ s)
            )



-- FEATURE DETAIL


type alias FeatureDetail =
    { name : String
    , filename : String
    , description : List String
    , tags : List String
    , background : Maybe BackgroundData
    , scenarios : List ScenarioData
    , rules : List RuleData
    }


type alias BackgroundData =
    { steps : List StepData
    }


type alias ScenarioData =
    { name : String
    , tags : List String
    , steps : List StepData
    }


type alias StepData =
    { keyword : String
    , name : String
    , stepType : String
    , index : Int
    , hasParams : Bool
    , params : List ParamDefData
    }


type alias ParamDefData =
    { name : String
    , paramType : String
    , min : Maybe Float
    , max : Maybe Float
    , choices : Maybe (List String)
    }


type alias RuleData =
    { name : String
    , tags : List String
    , scenarios : List ScenarioData
    }


featureDetailDecoder : D.Decoder FeatureDetail
featureDetailDecoder =
    D.map7 FeatureDetail
        (D.field "name" D.string)
        (D.field "filename" D.string)
        (D.field "description" (D.list D.string))
        (D.field "tags" (D.list D.string))
        (D.field "background" (D.nullable backgroundDecoder))
        (D.field "scenarios" (D.list scenarioDecoder))
        (D.field "rules" (D.list ruleDecoder))


backgroundDecoder : D.Decoder BackgroundData
backgroundDecoder =
    D.map BackgroundData
        (D.field "steps" (D.list stepDecoder))


scenarioDecoder : D.Decoder ScenarioData
scenarioDecoder =
    D.map3 ScenarioData
        (D.field "name" D.string)
        (D.field "tags" (D.list D.string))
        (D.field "steps" (D.list stepDecoder))


stepDecoder : D.Decoder StepData
stepDecoder =
    D.map6 StepData
        (D.field "keyword" D.string)
        (D.field "name" D.string)
        (D.field "stepType" D.string)
        (D.field "index" D.int)
        (D.field "hasParams" D.bool)
        (D.field "params" (D.list paramDefDecoder))


paramDefDecoder : D.Decoder ParamDefData
paramDefDecoder =
    D.map5 ParamDefData
        (D.field "name" D.string)
        (D.field "type" D.string)
        (D.field "min" (D.nullable D.float))
        (D.field "max" (D.nullable D.float))
        (D.field "choices" (D.nullable (D.list D.string)))


ruleDecoder : D.Decoder RuleData
ruleDecoder =
    D.map3 RuleData
        (D.field "name" D.string)
        (D.field "tags" (D.list D.string))
        (D.field "scenarios" (D.list scenarioDecoder))



-- PLAN DATA


type alias PlanResponse =
    { exists : Bool
    , data : Maybe PlanData
    }


type alias PlanData =
    { feature : String
    , scenarios : List PlanScenario
    }


type alias PlanScenario =
    { scenario : String
    , steps : List PlanStep
    }


type alias PlanStep =
    { step : String
    , params : Maybe PlanParams
    }


type alias PlanParams =
    List ( String, PlanValue )


type PlanValue
    = PlanFloat Float
    | PlanInt Int
    | PlanString String
    | PlanBool Bool
    | PlanNull


planResponseDecoder : D.Decoder PlanResponse
planResponseDecoder =
    D.map2 PlanResponse
        (D.field "exists" D.bool)
        (D.field "data" (D.nullable planDataDecoder))


planDataDecoder : D.Decoder PlanData
planDataDecoder =
    D.map2 PlanData
        (D.field "feature" D.string)
        (D.field "scenarios" (D.list planScenarioDecoder))


planScenarioDecoder : D.Decoder PlanScenario
planScenarioDecoder =
    D.map2 PlanScenario
        (D.field "scenario" D.string)
        (D.field "steps" (D.list planStepDecoder))


planStepDecoder : D.Decoder PlanStep
planStepDecoder =
    D.map2 PlanStep
        (D.field "step" D.string)
        (D.oneOf
            [ D.field "params" (D.nullable (D.keyValuePairs planValueDecoder))
            , D.succeed Nothing
            ]
        )


planValueDecoder : D.Decoder PlanValue
planValueDecoder =
    D.oneOf
        [ D.int |> D.map PlanInt
        , D.float |> D.map PlanFloat
        , D.bool |> D.map PlanBool
        , D.string |> D.map PlanString
        , D.null PlanNull
        ]



-- UPDATE RESPONSE


type alias UpdateResponse =
    { status : String
    , message : Maybe String
    }


updateResponseDecoder : D.Decoder UpdateResponse
updateResponseDecoder =
    D.map2 UpdateResponse
        (D.field "status" D.string)
        (D.oneOf
            [ D.field "message" (D.nullable D.string)
            , D.succeed Nothing
            ]
        )



-- HELPERS


planValueToString : PlanValue -> String
planValueToString pv =
    case pv of
        PlanFloat f ->
            String.fromFloat f

        PlanInt i ->
            String.fromInt i

        PlanString s ->
            s

        PlanBool b ->
            if b then
                "true"

            else
                "false"

        PlanNull ->
            ""
