## ADDED Requirements

### Requirement: Distill prompt is a generic per-dimension template

The `distill` scenario's `system_prompt_template` SHALL be a generic template that works for any single dimension, using `{{dimension}}` and `{{dimension_prompt}}` variables instead of hardcoding all 7 dimensions.

#### Scenario: Template renders correctly for any dimension
- **WHEN** the distill template is rendered with `dimension="句式特征"` and `dimension_prompt="分析句式特点：长短句比例、修辞手法、句式多样性、节奏感。"`
- **THEN** the rendered system prompt references only "句式特征" and does NOT mention other dimensions like "语气特点" or "词汇偏好"

#### Scenario: Template accepts articles_content
- **WHEN** the template is rendered with `articles_content` containing reference articles
- **THEN** the articles appear in the rendered system prompt

### Requirement: Distill output is writing guidance, not analysis

Each per-dimension LLM call SHALL output concise writing guidance instructions (3-5 directives, each 15-30 characters), using imperative tone such as "应...", "避免...", "倾向于...", "多...少...". The output MUST NOT include analysis reasoning or explanations.

#### Scenario: Output format is instructional
- **WHEN** the distill LLM responds for dimension "句式特征"
- **THEN** the response contains directive-style sentences like "应长短句参差使用" rather than analytical prose like "该作者倾向于使用长短句交替的方式..."

#### Scenario: Output excludes analysis reasoning
- **WHEN** the distill LLM responds for any dimension
- **THEN** the response does NOT contain phrases like "这是因为" or "可以看出" or "分析发现"

### Requirement: Distill summary text assembles as writing guide

The `style_profile` text assembly in `tasks.py` SHALL format the 7-dimension results as a cohesive writing guide, using `##` markdown headings for each dimension label with updated instructional labels.

#### Scenario: Summary uses writing-guide labels
- **WHEN** all 7 dimensions complete successfully
- **THEN** the assembled `style_profile` text uses labels like "## 思维模式" and "## 结构模式" and does NOT use analysis-style labels like "【思维特征】"

#### Scenario: Summary is compact
- **WHEN** dimension results are assembled into `style_profile`
- **THEN** dimensions are joined with no more than one blank line between sections
