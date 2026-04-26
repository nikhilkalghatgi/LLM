Title: With generative AI, don’t believe the hype (or the anti-hype)
Source: https://www.ibm.com/think/insights/with-generative-ai-dont-believe-the-hype-or-the-anti-hype
Date: 2026

No technology in human history has seen as much interest in such a short time as generative AI (gen AI). Many leading tech companies are pouring billions of dollars into training large language models (LLMs). But can this technology justify the investment? Can it possibly live up to the hype?

High hopes
Back in the spring of 2023—quite a long time in the artificial intelligence (AI) space—Goldman Sachs released a report estimating that the emergence of generative AI could boost global GDP by 7% annually, amounting to more than an additional USD 7 trillion each year.

How might generative AI achieve this? The applications of this technology are numerous, but they can generally be described as improving the efficiency of communication between humans and machines. This improvement will lead to the automation of low-level tasks and the augmentation of human abilities, enabling workers to accomplish more with greater proficiency.

Because of the wide-ranging applications and complexity of generative AI, many media reports might lead readers to believe that the technology is an almost magical cure-all. Indeed, this perspective characterized much of the coverage around generative AI as the release of ChatGPT and other tools mainstreamed the technology in 2022, with some analysts predicting that we were on the brink of a revolution that would reshape the future of work.

4 crises
Not even 2 years later, media enthusiasm around generative AI has cooled slightly. In June, Goldman Sachs released another report  with a more measured assessment, questioning whether the benefits of generative AI could justify the trillion-dollar investment in its development. The Financial Times, among other outlets, published an op-ed with a similarly skeptical view. The IBM Think Newsletter team summarized and responded to some of these uncertainties in an earlier post.

Subsequent stock market fluctuations led several analysts to proclaim that the “AI bubble” was about to pop and that a market correction on the scale of the dot-com collapse of the ‘90s might follow.

The media skepticism around generative AI can be roughly broken down into 4 distinct crises developers face:

The data crisis: The vast troves of data used to train LLMs are diminishing in value. Publishers and online platforms are locking up their data, and our demand for training data might soon exhaust the supply.
The compute crisis: The demand for graphics processing units (GPUs) to process this data is leading to a bottleneck in chip supply.
The power crisis: Companies developing the largest LLMs are consuming more power every year, and our current energy infrastructure is not equipped to keep up with the demand.
The use case crisis: Generative AI has yet to find its “killer app” in the enterprise context. Some especially pessimistic critics suggest that future applications might not meaningfully extend beyond “parlor trick” status.
These are serious hurdles, but many remain optimistic that solving the last problem (use cases) will help resolve the other 3. The good news is, they are already identifying and working on meaningful use cases.

Stepping outside the hype cycle
“Generative AI is having a marked, measurable impact on ourselves and our clients, fundamentally changing the way that we work,” says IBM distinguished engineer Chris Hay. “This is across all industries and disciplines, from transforming HR processes and marketing transformations through branded content to contact centers or software development.” Hay believes we are in the corrective phase that often follows a period of rampant enthusiasm, and perhaps the recent media pessimism can be seen as an attempt to balance out earlier statements that, in hindsight, seem like hype.

“I wouldn’t want to be that analyst,”says Hay, referencing one of the gloomier recent prognostications about the future of AI. “I wouldn’t want to be the person who says, ‘AI is not going to do anything useful in the next 10 years,’ because you’re going to be quoted on that for the rest of your life.”

Such statements might prove as shortsighted as claims that the early internet wouldn’t amount to much or IBM founder Thomas Watson’s 1943 guess that the world wouldn’t need more than 5 computers. Hay argues that part of the problem is that the media often conflates gen AI with a narrower application of LLM-powered chatbots such as ChatGPT, which might indeed not be equipped to solve every problem that enterprises face.

Overcoming limitations and working within them
If we start to run into supply bottlenecks—whether in data, compute or power—Hay believes that engineers will get creative to resolve these impediments.

“When you have an abundance of something, you consume it,” says Hay. “If you’ve got hundreds of thousands of GPUs sitting around, you’re going to use them. But when you have constraints, you become more creative.”

For example, synthetic data represents a promising way to address the data crisis. This data is created algorithmically to mimic the characteristics of real-world data and can serve as an alternative or supplement to it. While machine learning engineers must be careful about overusing synthetic data, a hybrid approach might help overcome the scarcity of real-world data in the short term. For instance, the recent Microsoft PHI-3.5 models or Hugging Face SMOL models have been trained with substantial amounts of synthetic data, resulting in highly capable small models.

Today’s LLMs are power-hungry, but there’s little reason to believe that current transformers are the final architecture. SSM-based models, such as Mistral Codestral Mamba, Jamba 1.5 or Falcon Mamba 1.5, are gaining popularity due to their increased context length capabilities. Hybrid architectures that use multiple types of models are also gaining traction. Beyond architecture, engineers are finding value in other methods, such as quantization, chips designed specifically for inference, and fine-tuning, a deep learning technique that involves adapting a pretrained model for specific use cases.

“I’d love to see more of a community around fine-tuning in the industry, rather than the pretraining,” says Hay. “Pretraining is the most expensive part of the process. Fine-tuning is so much cheaper, and you can potentially get a lot more value out of it.”

Hay suggests that in the future, we might have more GPUs than we know what to do with because our techniques have become much more efficient. He recently experimented with turning a personal laptop into a machine capable of training models. By rebuilding more efficient data pipelines and tinkering with batching, he is figuring out ways to work within the limitations. He could naturally do all this on an expensive H100 Tensor Core GPU, but a scarcity mindset enabled him to find more efficient ways to achieve the wanted results. Necessity was the mother of invention.

Thinking smaller
Models are becoming smaller and more powerful.

“If you look at the smaller models of today, they’re trained with more tokens than the larger models of last year,” says Hay. “People are stuffing more tokens into smaller models, and those models are becoming more efficient and faster.”

“When we think about applications of AI to solve real business problems, what we find is that these specialty models are becoming more important,” says Brent Smolinksi, IBM’s Global Head of Tech, Data and AI Strategy. These include so-called small language models and non-generative models, such as forecasting models, which require a narrower data set. In this context, data quality often outweighs quantity. Also, these specialty models consume less power and are easier to control.

“A lot of research is going into developing more computationally efficient algorithms,” Smolinksi adds. More efficient models address all 4 of the proposed crises: they consume less data, power and compute, and being faster, they open up new use cases.

“The LLMs are great because they have a very natural conversational interface, and the more data you feed in, the more natural the conversation feels,” says Smolinksi. “But these LLMs are, in the context of narrow domains or problems, subject to hallucinations, which is a real problem. So, our clients are often opting for small language models, and if the interface isn’t perfectly natural, that’s OK because for certain problems, it doesn’t need to be.”

Agentic workflows
Generative AI might not be a cure-all, but it is a powerful tool in the belt. Consider the agentic workflow, which refers to a multi-step approach to using LLMs and AI agents to perform tasks. These agents act with a degree of independence and decision-making capability, interacting with data, systems and sometimes people, to complete their assigned tasks. Specialized agents can be designed to handle specific tasks or areas of expertise, bringing in deep knowledge and experience that LLMs might lack. These agents can either draw on more specialized data or integrate domain-specific algorithms and models.

Imagine a telecommunications company where an agentic workflow orchestrated by an LLM efficiently manages customer support inquiries. When a customer submits a request, the LLM processes the inquiry, categorizes the issue, and triggers specific agents to handle various tasks. For instance, one agent retrieves the customer’s account details and verifies the information provided, while another diagnoses the problem, such as running checks on the network or examining billing discrepancies.

When the issue is identified, a third agent formulates a solution, whether that’s resetting equipment, offering a refund or scheduling a technician visit. The LLM then assists a communication agent in generating a personalized response to the customer, helping to ensure that the message is clear and consistent with the company’s brand voice. After resolving the issue, a feedback loop is initiated, where an agent collects customer feedback to determine satisfaction. If the customer is unhappy, the LLM reviews the feedback and might trigger other follow-up actions, such as a call from a human agent.

LLMs, while versatile, can struggle with tasks that require deep domain expertise or specialized knowledge, especially when these tasks fall outside the LLM’s training data. They are also slow and not well-suited for making real-time decisions in dynamic environments. In contrast, agents can operate autonomously and proactively, in real time, by using simpler decision-making algorithms.

Agents, unlike large, monolithic LLMs, can also be designed to learn from and adapt to their environment. They can use reinforcement learning or feedback loops to improve performance over time, adjusting strategies based on the success or failure of previous tasks. Agentic workflows themselves generate new data, which can then be used for further training.

This scenario highlights how an LLM is a useful part of solving a business problem, but not the entire solution. This is good news because the LLM is often the costliest piece of the value chain.

Looking past the hype
Smolinksi argues that people often go to extremes when excited about new technology. We might think a new technology will transform the world, and when it fails to do so, we might become overly pessimistic.

“I think the answer is somewhere in the middle,” he says, arguing that AI needs to be part of a broader strategy to solve business problems. “It’s usually never AI by itself, and even if it is, it’s using possibly multiple types of AI models that you’re applying in tandem to solve a problem. But you need to start with the problem. If there’s an AI application that could have a material impact on your decision-making ability that would, in turn, lead to a material financial impact, focus on those areas, and then figure out how to apply the right set of technologies and AI. Leverage the full toolkit, not just LLMs, but the full breadth of tools available.”

As for the so-called “use case crisis”, Hay is confident that even more compelling use cases justifying the cost of these models will emerge.

“If you wait until the technology is perfect and only enter the market once everything is normalized, that’s a good way to be disrupted,” he says. “I’m not sure I’d take that chance.”