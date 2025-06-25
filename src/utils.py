from typing import Optional, Union, List, Dict, Any
from pathlib import Path
import base64
from enum import Enum
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import LLMChain, SequentialChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import concurrent.futures
from dotenv import load_dotenv

load_dotenv()  # .env ファイルから環境変数を読み込み

# 他のプロバイダ向けも同様にインポート可能
# from langchain_deepseek import ChatDeepSeek
# from langchain_anthropic import ChatAnthropic


# Enum 定義（ワークフローの種類）
class WORKFLOW(Enum):
    PROMPT = "prompt"
    ROUTING = "routing"
    PARALLEL = "parallel"
    ORCHESTRATION = "orchestration"
    EVALUATION_OPTIMIZER = "evaluation"
    IMAGE = "image"


########################################
# 1. サンプル
########################################
def sample(
    workflow: WORKFLOW,
    topic: str = "ブロックチェーン",
    routingQuestion: Optional[str] = None,
    parallelTask: Optional[str] = None,
    orchestrationTask: Optional[str] = None,
    evaluationQuestion: Optional[str] = None,
    imagePrompt: Optional[str] = None,
    imagePath: Optional[str] = None,
    additionalImages: Optional[List[str]] = None,
    imageUrl: Optional[str] = None,
    additionalUrls: Optional[List[str]] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> None:
    if workflow == WORKFLOW.PROMPT:
        print("=== プロンプトチェーン ===")
        print(
            "説明: 指定されたトピックに基づいて、一連のプロンプトチェーンを実行します。"
        )
        print(prompt_chain_workflow(topic, provider=provider, model=model))
    elif workflow == WORKFLOW.ROUTING:
        print("\n=== ルーティング ===")
        print(
            "説明: トピックに対して質問形式に変換し、適切なルーティング処理を行います。"
        )
        actualRoutingQuestion = (
            routingQuestion if routingQuestion is not None else f"{topic}とは？"
        )
        print(
            routing_workflow(
                question=actualRoutingQuestion, provider=provider, model=model
            )
        )
    elif workflow == WORKFLOW.PARALLEL:
        print("\n=== 並列化 ===")
        print("説明: 複数のサブタスクを並列に実行し、処理の効率化を図ります。")
        subtasks = [f"{i} * 100 = ?" for i in range(5)]
        actualParallelTask = (
            parallelTask if parallelTask is not None else "計算してください"
        )
        print(
            parallel_workflow(
                task=actualParallelTask,
                subtasks=subtasks,
                provider=provider,
                model=model,
            )
        )
    elif workflow == WORKFLOW.ORCHESTRATION:
        print("\n=== オーケストレーション ===")
        print(
            "説明: 複数のタスクをシーケンシャルに連携して実行し、全体の流れを管理します。"
        )
        actualOrchestrationTask = (
            orchestrationTask
            if orchestrationTask is not None
            else "\n".join(f"問{i}. 100 * {i} = ?" for i in range(5))
        )
        print(
            orchestration_workflow(
                task=actualOrchestrationTask, provider=provider, model=model
            )
        )
    elif workflow == WORKFLOW.EVALUATION_OPTIMIZER:
        print("\n=== 自律型評価オプティマイザー ===")
        print("説明: 自律的に評価を行い、最適化されたフィードバックを提供します。")
        actualEvaluationQuestion = (
            evaluationQuestion if evaluationQuestion is not None else topic
        )
        print(
            evaluation_optimizer_workflow(
                question=actualEvaluationQuestion, provider=provider, model=model
            )
        )
    elif workflow == WORKFLOW.IMAGE:
        print("\n=== 画像解析 ===")
        print("説明: 画像を解析して説明文を生成します。")
        actualImagePrompt = (
            imagePrompt
            if imagePrompt is not None
            else "これらの画像の違いを説明してください。"
        )
        actualImagePath = imagePath if imagePath is not None else None
        actualAdditionalImages = (
            additionalImages if additionalImages is not None else None
        )
        resultImage = analyze_image(
            prompt=actualImagePrompt,
            image_path=actualImagePath,
            additional_images=actualAdditionalImages,
            image_url=imageUrl,
            additional_urls=additionalUrls,
            provider=provider,
            model=model,
        )
        print(resultImage)
    else:
        print("Unknown workflow. 指定されたワークフローが認識されません。")


def get_llm(
    provider: str = None, model: str = None, reasoning_effort: str = None, **kwargs
):
    # provider が未指定の場合は "gemini" をデフォルトとする
    if not provider:
        provider = "gemini"
        # provider = "openai"
    # model が未指定の場合、provider に応じたデフォルト値を設定する
    if not model:
        if provider == "openai":
            model = "o3-mini"
        elif provider == "gemini":
            model = "gemini-2.0-flash"

    print(f"provider: {provider}, model: {model}")
    if provider == "openai":
        return ChatOpenAI(model=model, reasoning_effort=reasoning_effort, **kwargs)
    elif provider == "gemini":
        return ChatGoogleGenerativeAI(model=model, **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def create_chain(llm, prompt_str: str, output_key: str):
    prompt_template = ChatPromptTemplate.from_messages([("human", prompt_str)])
    return LLMChain(llm=llm, prompt=prompt_template, output_key=output_key)


def get_chain(
    prompt_str: str, output_key: str, provider: str = None, model: str = None, **kwargs
):
    """
    プロンプト文字列と出力キーを必須パラメータとし、オプションで provider と model を指定可能にします。
    provider, model が未指定の場合、get_llm 内でデフォルト値が設定されます。
    """
    llm_instance = get_llm(provider, model=model, **kwargs)
    return create_chain(llm_instance, prompt_str, output_key)


def question(topic: str, provider: str = None, model: str = None):
    results = simple(topic, provider, model)
    return results[0]


########################################
# 0. シンプル
########################################
def simple(
    topic: Union[str, List[str]],
    provider: str = None,
    model: str = None,
):
    # topicがstrならリスト化
    if isinstance(topic, str):
        topics = [topic]
    else:
        topics = topic

    results = []
    for t in topics:
        chains = []  # チェーンを格納するリスト
        chains.append(
            get_chain(
                provider=provider if provider is not None else "gemini",
                model=model if model is not None else "gemini-2.0-flash",
                prompt_str="{topic}",
                output_key="explanation",
            )
        )

        # 2つ目以降のチェーンを追加したい場合はここでappend
        # chains.append(
        #     get_chain(
        #         provider=provider if provider is not None else "gemini",
        #         model=model if model is not None else "gemini-2.0-flash",
        #         prompt_str="上記の説明を踏まえて、関連する具体例を一つ挙げてください。説明: {explanation}",
        #         output_key="example",
        #     )
        # )

        # SequentialChainを作成
        overall_chain = SequentialChain(
            chains=chains,
            input_variables=["topic"],
            output_variables=["explanation"],
            # output_variables=["explanation", "example"],
        )

        result = overall_chain.invoke({"topic": t})
        print(f"{t}: {result['explanation']}")
        results.append(result["explanation"])
        # print(result["example"])
    return results


########################################
# 1. プロンプトチェーン (Prompt Chain)
########################################
def prompt_chain_workflow(topic: str, provider: str = None, model: str = None):
    # Step1: 全体の構成やアウトラインを生成
    chainOutline = get_chain(
        prompt_str="トピック「{topic}」について、全体の構成やアウトラインを生成してください。",
        output_key="outline",
        provider=provider,
        model=model,
    )
    # アウトライン生成の呼び出し
    outlineResult = chainOutline.invoke({"topic": topic})
    outlineText = outlineResult.get("outline", "").strip()
    if not outlineText:
        raise ValueError(
            f"エラー: トピック '{topic}' に対するアウトライン生成に失敗しました。返却されたアウトラインが空です。"
        )

    # 生成されたアウトラインを空行で区切って各トピックごとにセクション分割し、
    # 同じトピック内の改行はスペースに置換して1行にまとめる
    sections = [
        section.replace("\n", " ").strip()
        for section in outlineText.split("\n\n")
        if section.strip()
    ]
    if not sections:
        raise ValueError(
            f"エラー: アウトラインの分割に失敗しました。期待されるセクションが見つかりません。アウトライン内容: {outlineText}"
        )

    # Step2: 各セクションごとに詳細な文章を個別のLLM呼び出しで生成
    detailSections = []
    for section in sections:
        # 個別セクションの文章生成チェーンを作成
        chainSection = get_chain(
            prompt_str="以下のセクションの内容を詳細に執筆してください:\n{section}",
            output_key="detail",
            provider=provider,
            model=model,
        )
        # セクションの詳細文章生成を実行
        detailResult = chainSection.invoke({"section": section})
        detailText = detailResult.get("detail", "").strip()
        if not detailText:
            raise ValueError(
                f"エラー: セクション '{section}' の文章生成に失敗しました。返却された文章が空です。"
            )
        detailSections.append(detailText)

    # Step3: 各セクションの詳細文章を統合し、全体として整合性のある文章に補正・チェックする
    combinedDetails = "\n".join(detailSections)
    integrationChain = get_chain(
        prompt_str="以下は各セクションの文章です。これらを統合し、全体として整合性のある文章に補正してください:\n{details}",
        output_key="finalOutput",
        provider=provider,
        model=model,
    )
    finalResult = integrationChain.invoke({"details": combinedDetails})
    finalOutput = finalResult.get("finalOutput", "").strip()
    if not finalOutput:
        raise ValueError(
            "エラー: 統合および補正処理により最終文章の生成に失敗しました。"
        )

    return {"outline": outlineText, "finalOutput": finalOutput}


########################################
# 2. ルーティング (Routing)
########################################
def routing_workflow(
    question: str, provider: Optional[str] = None, model: Optional[str] = None
):
    # Step1: 質問を分類するチェーンを作成
    classify_chain = get_chain(
        prompt_str=(
            "次の質問を、一般的な質問か専門的な質問かに分類してください。"
            "\n質問: {question}\n出力は 'general' か 'specialized' のどちらかのみで。"
        ),
        output_key="category",
        provider=provider,
        model=model,
    )
    classification = classify_chain.invoke({"question": question})
    category = classification["category"].strip().lower()

    # Step2: 分類結果に基づき、回答チェーンを切り替え
    if category == "general":
        print("general")
        answer_chain = get_chain(
            prompt_str="次の質問に簡潔に答えてください:\n{question}",
            output_key="answer",
            provider=provider,
            model=model,
        )
    elif category == "specialized":
        print("specialized")
        answer_chain = get_chain(
            prompt_str="次の専門的な質問に、詳細に答えてください:\n{question}",
            output_key="answer",
            provider=provider,
            model=model,
        )
    else:
        return {"error": "質問の分類に失敗しました。"}

    answer_result = answer_chain.invoke({"question": question})
    answer_result["category"] = category
    return answer_result


########################################
# 3. 並列化 (Parallelization)
########################################
def parallel_workflow(
    task: str,
    subtasks: list,
    provider: Optional[str] = None,
    model: Optional[str] = None,
):
    # サブタスク毎に独立したチェーンを作成し、並列に処理する関数
    def process_subtask(subtask: str):
        # 各サブタスクに対してget_chain関数を呼び出し、providerとmodelを渡す
        chain = get_chain(
            prompt_str="タスク「{subtask}」に対して、{task}",
            output_key="result",
            provider=provider,
            model=model,
        )
        return chain.invoke({"subtask": subtask, "task": task})["result"]

    results = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_subtask = {
            executor.submit(process_subtask, st): st for st in subtasks
        }
        for future in concurrent.futures.as_completed(future_to_subtask):
            st = future_to_subtask[future]
            try:
                results[st] = future.result()
            except Exception as exc:
                results[st] = f"Error: {exc}"
    return {"task": task, "subtask_results": results}


########################################
# 4. オーケストレーション (Orchestration)
########################################
def orchestration_workflow(
    task: str, provider: Optional[str] = None, model: Optional[str] = None
):
    """
    オーケストレーション ワークフロー関数
    この関数は、与えられたタスクをサブタスクに分解し、各サブタスクを並列処理した後、
    統合チェーンを用いて最終的な回答を生成します。

    @param task: タスクの内容 (str)
    @param provider: 使用するLLMプロバイダの識別子。未指定の場合はデフォルト値を使用 (Optional[str])
    @param model: 利用するLLMモデル名。未指定の場合はデフォルト値を使用 (Optional[str])
    @return: タスクの分解結果、各サブタスクの結果、統合後の最終回答を含む辞書 (Dict[str, Any])
    """
    # Step1: タスク分解チェーン（サブタスクはカンマ区切りの文字列で返ると仮定）
    decompose_chain = get_chain(
        prompt_str="次のタスクを実行するためのサブタスクに分解してください。サブタスクはカンマ区切りで出力してください。\nタスク: {task}",
        output_key="subtasks",
        provider=provider,
        model=model,
    )
    decomp_result = decompose_chain.invoke({"task": task})
    subtasks_str = decomp_result["subtasks"]
    subtasks = [st.strip() for st in subtasks_str.split(",") if st.strip()]

    # Step2: 各サブタスクを並列に処理する
    def process_subtask(st: str) -> str:
        """
        サブタスクごとの詳細な回答を生成する関数
        @param st: サブタスクの内容 (str)
        @return: サブタスクの処理結果 (str)
        """
        chain = get_chain(
            prompt_str="サブタスク「{subtask}」に対して、詳細な回答を生成してください。",
            output_key="result",
            provider=provider,
            model=model,
        )
        return chain.invoke({"subtask": st})["result"]

    subtask_results = {}
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_st = {executor.submit(process_subtask, st): st for st in subtasks}
        for future in concurrent.futures.as_completed(future_to_st):
            st = future_to_st[future]
            try:
                subtask_results[st] = future.result()
            except Exception as exc:
                subtask_results[st] = f"Error: {exc}"

    # Step3: 統合チェーンで最終回答を生成
    aggregation_chain = get_chain(
        prompt_str="以下のサブタスク結果を統合して、最終的な回答を生成してください:\n{subtask_results}",
        output_key="final_answer",
        provider=provider,
        model=model,
    )
    aggregation_result = aggregation_chain.invoke(
        {"subtask_results": str(subtask_results)}
    )

    return {
        "decomposition": subtasks,
        "subtask_results": subtask_results,
        "final_answer": aggregation_result["final_answer"],
    }


########################################
# 5. 自律型評価オプティマイザー (Autonomous Evaluation Optimizer)
########################################
def evaluation_optimizer_workflow(
    question: str,
    iterations: int = 2,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    # 初期回答生成チェーンの構築
    init_chain = get_chain(
        prompt_str="次の質問に対する初期回答を生成してください:\n{question}",
        output_key="answer",
        provider=provider,
        model=model,
    )
    current_answer = init_chain.invoke({"question": question})["answer"]

    # 指定回数だけ評価・改善を反復
    for i in range(iterations):
        # 評価チェーンの構築
        eval_chain = get_chain(
            prompt_str="以下の回答を評価し、改善点をフィードバックしてください:\n回答: {answer}",
            output_key="feedback",
            provider=provider,
            model=model,
        )
        feedback = eval_chain.invoke({"answer": current_answer})["feedback"]

        # 改善チェーンの構築
        refine_chain = get_chain(
            prompt_str=(
                "次の質問に対して、以下のフィードバックを踏まえて回答を改善してください。\n"
                "質問: {question}\nフィードバック: {feedback}"
            ),
            output_key="answer",
            provider=provider,
            model=model,
        )
        current_answer = refine_chain.invoke(
            {"question": question, "feedback": feedback}
        )["answer"]

    return {"final_answer": current_answer, "latest_feedback": feedback}


########################################
# 6. 画像分析
########################################
def analyze_image(
    prompt: str,
    image_path: Optional[Union[str, Path]] = None,
    image_url: Optional[str] = None,
    provider: str = None,
    model: Optional[str] = None,
    additional_images: Optional[List[Union[str, Path]]] = None,
    additional_urls: Optional[List[str]] = None,
) -> str:
    # 少なくとも1つの画像ソースが必要
    if not image_path and not image_url:
        raise ValueError("少なくとも1つの画像パスまたはURLを指定してください")

    # プロバイダとモデルの設定
    if provider is not None and provider.lower() == "openai" and model is None:
        model = "gpt-4o"
    llm = get_llm(provider, model=model)

    # メッセージコンテンツの準備
    content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]

    # ローカル画像ファイルの処理
    if image_path:
        content.append(_process_local_image(image_path))

    # 画像URLの処理
    if image_url:
        content.append(_process_image_url(image_url))

    # 追加の画像の処理
    if additional_images:
        for img_path in additional_images:
            content.append(_process_local_image(img_path))

    # 追加のURLの処理
    if additional_urls:
        for url in additional_urls:
            content.append(_process_image_url(url))

    # メッセージの作成と実行
    message = HumanMessage(content=content)
    response = llm.invoke([message])

    return response.content


def _process_local_image(image_path: Union[str, Path]) -> Dict[str, Any]:
    """ローカル画像ファイルをbase64エンコードしてメッセージコンテンツに変換"""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")

    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")

    mime_type = _get_mime_type(image_path)
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
    }


def _process_image_url(url: str) -> Dict[str, Any]:
    """画像URLをメッセージコンテンツに変換"""
    return {"type": "image_url", "image_url": {"url": url}}


def _get_mime_type(image_path: Path) -> str:
    """ファイル拡張子からMIMEタイプを推測"""
    extension = image_path.suffix.lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    #  未知の拡張子の場合はデフォルトのjpegを返す
    return mime_types.get(extension, "image/jpeg")  # デフォルトはjpeg
