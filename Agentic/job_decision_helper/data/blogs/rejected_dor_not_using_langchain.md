Title: Rejected for not using LangChain/LangGraph?
Source: Reddit
Date: 2026


### **BobbyL2k** *( 5mo ago )*

No, you’re not missing anything. Well, maybe you missed that position… jokes aside, LangChain and LangGraph are poor abstractions anyway. At work we have a custom internal library which does the same thing but better.

The company you mentioned is probably not technical enough to understand the issues in LangChain and LangGraph.


### **dougeeai** *( 5mo ago )*

Thanks I really needed this. Being told I'm "not technical enough" had me questioning if I'd strayed too far from industry standards. Good to know others see the value in building custom solutions over these abstractions.


### **positivitittie** *( 5mo ago )*

Yep. Dodged a bullet.


### **Creative-Type9411** *( 5mo ago )*

sounds like they really could've used him too 👀


### **vtkayaker** *( 5mo ago )*

Remember, interviews are a two-sided process. You're interviewing them, too, and they can absolutely fail an interview.

Sometimes this happens because a potential employer is painfully stupid, or obviously dysfunctional, or any number of other things. Other times it happens because the employer is simply a bad match.

You have focused on lower-level skills, which bring real value. But those skills don't bring equal value to everyone. Some perfectly reasonable companies have zero business touching Tensorflow.

To have a successful career, you need to learn to match your skills to teams that will see big benefits, and that will ideally go on to do awesome things.


### **dougeeai** *( 5mo ago )*

Phenomenal advice, thank you


### **Repulsive-Memory-298** *( 5mo ago )*

it does seem kind of weird to bring up bare metal when someone asks about data movement in an agent stack… where do you see justification for this?


### **dougeeai** *( 5mo ago )*

Fair point. They asked about data movement in LangGraph specifically, and I responded that I don't use LangGraph in production, then pivoted to model optimization instead of addressing agent-to-agent communication patterns.

I could have discussed how I handle state management and inter-agent communication in my FastAPI setup, which would've been more apples-to-apples. But I just don't use the LangChain framework (never saw the value), my head isn't in that space, and I didn't think about the context in real time (no pun intended). But in hindsight I'm not even sure they would have been interested in my answer even if I had the presence of mind to pivot.


### **Jnorean** *( 5mo ago )*

Better that they didn't hire you for you. If they couldn't understand what you were saying then you would have never fit in with their level of technical understanding.


### **_raydeStar** *( 5mo ago )*

Llama 3.1

In the beginning of AI and local llms, LangChain was pretty good and it looked like it would become the standard.

But then - it didn't. Much better tools came out that left it in the dust. Because of this, it tells me the company you interviewed for is more legacy-focused and will not move quickly. The fact that they look down on you though - tells me that there is a lot of hubris there.


### **Prof_Tantalum** *( 5mo ago )*

I know nothing about it, but it sounds like they lost the person who put everything together and they need someone to take over the mess.


### **pawala7** *( 5mo ago )*

That's just their way of saying they're not technical enough. And it makes sense. If you were put in a team that only used LangChain or LangGraph, that would just be friction for everyone.


### **-dysangel-** *( 5mo ago )*

my boss is the same way. I was using the ChatGPT API and a vector database directly and he kept insisting that LangGraph would be magically better in some way


### **WoofNWaffleZ** *( 5mo ago )*

In agreement here. The company is not technical enough.

Stoic perspective: They saved you a ton of annoyance and saved you from a limited career by not hiring you.

Lots of crap companies out there that are just simply promoting. The advanced companies are building their own versions of langchain/langgraph to fit their specific needs to scale more effectively.


### **fogonthebarrow-downs** *( 5mo ago )*

I was in an AI role before. We also used an internal library which was much better. Someone should build that (but not me, I'm far too stupid and lazy)


### **vertigo235** *( 5mo ago )*

All this should tell you is that they are heavily invested in LangChain and LangGraph.


### **MrPecunius** *( 5mo ago )*

I recently got turned down for an LLM-oriented project because the non-technical person doing the interview was fixated on MCP being the solution for everything. That, and he felt I should basically vibe code the whole thing to "be more efficient".

They saved me the trouble of turning them down. Life is too short for that kind of aggravation, and I don't want to damage my reputation for delivering results on time and within budget.


### **SkyFeistyLlama8** *( 5mo ago )*

I think the funniest video I've seen had some Microsoft developer saying that if you don't need to use MCP or A2A, then don't. Agents run perfectly fine using hardcoded functions in Python. MCP introduces overhead and there's also the security headache of having an MCP server run authenticated requests on your behalf.


### **mr_happy_nice** *( 5mo ago )*

Omg thank you, a couple months ago i kinda went ahead with the plan for my set of projects to specifcally not use mcp for search and related research tasks because of the scaffolding i felt was heavy, and being told no, mcp is the future you must learn and use this.. Ha i think part of the issue is people seeing videos with a bunch of views or whatever saying You Have to Learn MCP Today!! Lol it just feels nice to have an intelligent person say the same thing i said, or i said that they said.. :)


### **dougeeai** *( 5mo ago )*

Sounds like they missed out on not grabbing you. But totally feel you here. I was starting to get some red flags that if everything proceeded and got to an offer stage there may have been other reservations.


### **segmond** *( 5mo ago )*

llama.cpp

If a company is asking for Langchain/LangGraph, that might be all they know. Your CUDA, PyTorch etc won't impress them. Do you want a job? Learn the stupid tool and be ready to use it and deal with it. That's the way the real world works. If you get in there and can prove you know your stuff you can then show them how to do better. But frankly, most orgs don't can't do the CUDA, Pytorch thing. A popular framework is often what they embrace, it's easy to hire for and easy to keep things consistent without homegrown framework.


### **MrCuntBitch** *( 5mo ago )*

This. I used to hate on langchain but my new job uses it heavily and I just don’t care or have the energy to complain anymore. works fine to be honest.


### **-dysangel-** *( 5mo ago )*

I agree it's fine, but the funny part is that anyone who can work with the "bare metal" equivalents will have zero issue using LangChain. It's the same concepts, just more framework agnostic.


### **pm_me_github_repos** *( 5mo ago )*

Depends if you want to work at the model layer or the application layer.

Most job opportunities are going to be at the application layer moving forward.

Working at the model layer is where specialized talent density is, but it’s far more exclusive.


### **Medium_Chemist_4032** *( 5mo ago )*

dodged a bullet


### **SkyFeistyLlama8** *( 5mo ago )*

Langchain? No shit, that's the messiest and most over-engineered LLM framework out there. Nobody needs that amount of abstraction when you're just doing API calls. There's nothing technical about throwing and receiving strings over HTTPS, lmao.

I'm starting to warm up to Microsoft's Agent Framework. It's good for workflows, a little messy for RAG but still usable, and the built-in agent patterns are great for prototyping. You dodged a bullet there and I'm sure your skill sets will be valued somewhere else.


### **rm-rf-rm** *( 5mo ago )*

over engineered is a term applicable for Japanese toilets. The applicable term for langchain is toilet.


### **a_slay_nub** *( 5mo ago )*

I would not want to work for any company that took langchain/langgraph seriously and wanted to use it in production. I've gone on a purge and am actively teaching my teammates how easy everything is outside of it.

Langchain is a burning pile of piss that doesn't even do demos well. It's an overly complex abstraction on simple problems with shit documentation and constantly changing code bases.


### **dougeeai** *( 5mo ago )*

Yeah as decent as the money might have been there were a few other red flags lined up with what your saying. Not gonna lie, hearing you say "Langchain is a burning pile of piss" is therapeutic lol


### **_bones__** *( 5mo ago )*

I only glanced at it, and don't do much LLM work anyway. But it seems there are about five different ways to set up the context, all of which boil down to "here's your prompt string" Fully un-opinionated, and thus kind of useless.


### **Solid_Owl** *( 5mo ago )*

THANK YOU.


### **rm-rf-rm** *( 5mo ago )*

And imagine that they are "valued at $1.25B" https://techcrunch.com/2025/10/21/open-source-agentic-startup-langchain-hits-1-25b-valuation/

The $10m seed +$25m series A a week later wasnt bad enough for stuff that is so bad that its worse than vaporware. Using it actually makes you develop slower.

Its truly an atrocity and stomach churning


### **Swolnerman** *( 5mo ago )*

Do you have any resources explaining why this is the case and how to move off of it? I work in langchain/langgraph and sadly had no idea it was shit


### **hyperdynesystems** *( 5mo ago )*

Found a pic of you, OP


### **dougeeai** *( 5mo ago )*

Wish I was that cool. But based on feedback can safely say I'll forego having Tank upload the Langchain program into my cerebrum.


### **hyperdynesystems** *( 5mo ago )*

The only reason I'd say to look at it is to know why you don't wanna use it. Admittedly I haven't used it since the early versions but what I saw I didn't like, specifically:

* Doing something common that was slightly different from the examples was basically a non-starter without diving into their existing classes and rewriting them (even for very simple stuff)

* If you did want to rewrite something in their existing code, it was annoying to do

* Under the hood it was using "ReAct" prompting, which spammed the context window with thousands of tokens to get it to do whatever it was trying to do, e.g., tool use

* The context flooding made it useless to the user as it'd bump their conversation out of the context window within 1-2 prompts

After wrestling it to do something very basic and then seeing the thousands of tokens it was wasting I said "nope" and looked for other options.


### **bick_nyers** *( 5mo ago )*

DSPy is better anyways, even if you use it for nothing else than strongly typed LLM outputs.

Also laughable to ask about "efficient data movement", brother these are strings and we aren't serving infra on microcontrollers.

Claude + OpenAI + Bedrock is a red flag that suggests to me that their "engineering" is just "use the best model". Not true of every company obviously.

The companies that do the deeper work are the ones that will come out on top in the long run.

If your company is a lightweight wrapper over chat gippity then you are going to get flanked by startups 7 ways to Sunday.


### **dougeeai** *( 5mo ago )*

"The companies that do the deeper work are the ones that will come out on top in the long run" - love that


### **AutomataManifold** *( 5mo ago )*

I've been using BAML for typed outputs lately. Vastly speeds up testing prompts if you use the VS Code integration.

Instructor and Outlines are also good.

I used DSPy for the typed outputs for a while but on a new project I'd pick it for the prompt optimization rather than just that. Still better than LangChain.


### **jiii95** *( 5mo ago )*

Llama 7B

Anything about ACE (Agent Context Engineering) ? Libraries and things likd that


### **AutomataManifold** *( 5mo ago )*

I generally agree with this: https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-03-own-your-context-window.md

I'm open to libraries to help manage context but I don't currently have one that I prefer.


### **BasilParticular3131** *( 5mo ago )*

Honestly I was wondering as well from OP's question, to what exactly is "efficient data movement" in LangGraph. The library handles data movement so poorly across nodes not to mention the side effects from their super step based node execution model. The only efficiency one can get is by moving actually less data.


### **Pvt_Twinkietoes** *( 5mo ago )*

No. You dodged a bullet. It's trash.


### **PsychohistorySeldon** *( 5mo ago )*

No. You dodged a bullet. This is just too funny


### **crazyenterpz** *( 5mo ago )*

LangChain and LangGraph  frameworks were fantastic when we were just getting started with using LLM. But they are hopelessly complicated now.

I can see your interviewers' point: they are invested in this ecosystem and they want someone who can keep the systems going.

edit : grammar


### **dougeeai** *( 5mo ago )*

Totally get the 'wrong-shaped peg' aspect. They're invested in their ecosystem and need someone who fits. Totally fair, just wish they would have put it in the posting. What made me uneasy was being labeled "not technical enough" just because I use a different approach. And an approach which offers me more control.

I'll grant I come from a DS rather than developer background and maybe this wasn't my best interview performance, but I've pushed some useful stuff in my domain. Communities like this are sometimes the only way I can keep my perspective straight!


### **crazyenterpz** *( 5mo ago )*

Don't worry about this rejection one bit.

My advice to you would be this and it is controversial: there are few LLM related jobs for experts in yTorch/CUDA/GGUF  . Most employers are merely consuming the LLM APIs rather than training models. My employer user Azure APIs to read documents and pass that to another model for data extraction and validation. Most companies are doing more or less the same thing

So maybe look at some High level/ API level abstraction frameworks. Langchain is overly complicated but others exist which may be a better fit.

Good Luck !


### **ahjorth** *( 5mo ago )*

That's the part that would bother me too. If you can do the low-level stuff, learning high-level abstractions is not hard. So I think they made a weird call by not seeing a value in that. But calling low-level "less technical" is just... objectively wrong, and I would have been fucking annoyed too. I hope the replies to your post make you feel vindicated, though. It was them, not you.


### **SkyFeistyLlama8** *( 5mo ago )*

Hey if you're coming from a DS background, look at how LLMs can be used to curate downstream data for business use cases.


### **inagy** *( 5mo ago )*

Is there any recommended alternative to LangChain/LangGraph which is more easy to get started with and doesn't try to solve everything all at once?


### **Charming_Support726** *( 5mo ago )*

There are a lot.

I personally use Agno because it is well structured and documented. But it is just a matter of preference.


### **crazyenterpz** *( 5mo ago )*

There are several .. I wanted to learn more deeply about the apis so I wrote wrappers for LLM tool calling with json output using each LLM's REST API. There are subtle differences between Anthropic, OpenAI and Gemini apis. DeepSeek adheres to OpenAI. Most LLM example show you how to invoke the API with curl or bash , and also python.

Pydantic is very useful for data issues.


### **dragongalas** *( 5mo ago )*

They did not need you.

They need fast developers, which churn out shit code, but which could be understood and supported by other devs. Efficiency is not an important point for this calibre of companies.


### **mr_birkenblatt** *( 5mo ago )*

To clarify: code efficiency is not needed. coding efficiency is needed. And you get a good mileage with pre baked solutions. Why invest time in optimizing stuff when you throw it all out next week to test out a different idea


### **mkwr123** *( 5mo ago )*

The other comments cover this well, but just to reiterate, a lot of companies mistake “AI Engineering” or more generally anything to do with LLMs with LangChain (and associated libraries/frameworks). Possibly because it’s their only exposure, but in any case it’s very frustrating and you’re better off not working in such a place anyway.


### **hashmortar** *( 5mo ago )*

Honestly depends a lot on the company and their processes. If they rely on those abstractions quite a bit then, not having that experience means you will be building code that will be outside the experience of folks you work with and then no one else can maintain it. So it’s not a reflection on you by any means, just misalignment with the team. Lots of companies use the abstractions so you may just want to just have that experience for just namesake.


### **dougeeai** *( 5mo ago )*

Totally get this, if you are a langchain shop, I'm just not your guy. Can leave emotions out of it. A mere misalignment. Just wish they would have put langchain in the post instead of explicitly mentioning pytorch. A classic disconnect.


### **Old-School8916** *( 5mo ago )*

this company is working on a higher layer abstraction than ya bud. it's just a different pool of devs I guess.

I don't like langchain either.


### **Torodaddy** *( 5mo ago )*

IMO You dont know why they rejected you, whatever they tell you likely is false. I wouldn't worry about it, being on the hiring side of things I've seen candidates rejected for the stupidest stuff, largely the process is finding reasons to reject rather than "is this person good enough" Everyone wants the cheap unicorn that doesn't have other offers.

True story I was at a firm that someone was rejected because of their first name "we already have a Frank" 🤯


### **its_just_andy** *( 5mo ago )*

lots of the comments are "lol langchain bad" (which is true) but the reality is, they wanted someone proficient in langchain or langgraph, and you're clearly not. So you would not have been a good fit for the role.

An ideal outcome will be - they find someone who suits their needs, and you find an employer who suits yours.


### **txgsync** *( 5mo ago )*

It's the same argument I've had on both sides of the table when interviewing candidates or being interviewed. My domain spans from the kernel through the business logic, and kind of ends at the user interface. If I'm interviewing for a job that expects me to be an expert in Next.js, I'm gonna bomb it... that's not where I work. But if you ask me how to build, cable, network, and orchestrate several thousand Linux nodes with fast SSD and a bunch of spinning disks into a Cassandra cluster with Kubernetes, I'm probably your guy.

And since I've spent the past year doing AI on bare GPUs in AWS and on my Mac? Probably in the same boat as you. LangChain/LangGraph feels like lipstick on a pig.

They're looking for someone who speaks "framework" not "fundamentals." Different religions, same god. You're not missing much.

TL;DR: You didn't fail the technical interview. You failed the culture fit.


### **AutomataManifold** *( 5mo ago )*

My only issue with that framing is that I'm not sure LangChain is an adequate framework, either. If they've already committed to the technical debt then it's a subk cost, but there's so many other better options out there...


### **DataScientia** *( 5mo ago )*

Many people suggest to use langchain, but it is not good. Too many level of abstraction.

But i want to know what was the purpose of pytorch /cuda /gguf for multi agent systems

Even big companies use model from openai /claude etc

For learning or research this approach is good. But as a company perspective just use llms from popular providers

Also apart from llm generating response, there is lot of work involved while creating multi system agent. So focus should be on that


### **grabber4321** *( 5mo ago )*

Nobody actually knows how to work with AI yet. Big companies are still struggling to implement actionable AI integration.

My bro works in a HUGE company and they continue having issues implementing AI on a meaningful level.

Sometimes you win, sometimes you lose.


### **LoSboccacc** *( 5mo ago )*

I mean you dodged a bullet but still you should lead with the equivalent topic used at wire level, just opening with "I work at a lower level with bare metal for better performance and control" instead of opening with "well I'm familiar with data sharing structure for efficient context management for large scale data processing, even without langraph, do you have specific scenario you want to explore?" has definitely different sounds. not that you'd wanted to work there but still.


### **dougeeai** *( 5mo ago )*

You're spot on.


### **Ok-Adhesiveness-4141** *( 5mo ago )*

Those guys are dumb. Probably aren't good at Python either.


### **radarsat1** *( 5mo ago )*

I get it but I also see that like 2/3 of the LLM-related jobs out there are requiring LangChain so I've been checking it out lately. So far my impression is that it's not bad? Seems to take care of a lot of things like a huge set of adaptors for different services, deals with embedding and storage and retrieval for you, etc.

Since I see a lot of negativity in this thread I'm wondering if someone can explain in more software engineering terms what the gotchas are with it, and what is better? For my honest knowledge, because I'm just getting into this stuff from having more of a writing-my-own-pytorch-models type of background. I'd like to go in to any potential messy situations with my eyes open.


### **interesting_vast-** *( 5mo ago )*

yes and no, should you be adopting for your personal use? probably not, should you be adopting/learning it for career purposes? yes, a lot of large corporations are trying to stay as far away from AI hardware investments as possible most of them are going to be using chatGPT/Claude through the API. At this point it’s not about what’s best it’s about what’s being used and companies are very much sticking to the “standards” LangChain, MCP Servers, etc.


### **ShengrenR** *( 5mo ago )*

I feel like a lot of folks learned early (with reason) to dislike/distrust langchain, but then just copied that notion over to langgraph when it came along - yes, they can be intertwined, yes they are by the same folks - but imo they did a better job with langgraph specifically - at least partly because they got to ride on the shoulders of google pregel to get there - I've never scaled huge with langgraph, but at least in small/mid sized projects it's done fine when mixed with other frameworks.


### **Significant_Post8359** *( 5mo ago )*

You dodged a bullet. They are looking with somebody with specific experience with a tech stack they were married to.

I’d rather work with a self starter who can adapt and asses best approaches.


### **ApricotBubbly4499** *( 5mo ago )*

Disagree with other commenters. This is a mark that you probably haven’t worked with enough use cases to understand the value of a framework for fast iteration.

No one is directly invoking PyTorch from fastapi in production for LLMs.


### **dougeeai** *( 5mo ago )*

Just wanted to clarify - I'm not invoking pytorch from fastapi for every inference request. I run optimized model servers (using GGUF/llama.cpp or others) with fastapi providing the orchestration layer.

My architecture includes:

A coordinator LLM that routes requests between specialized models, multiple specialized services (embeddings, domain-specific fine-tuned models, RAG-enhanced models), fastapie endpoints that both humans AND other AI services can call, each model service exposed via its own API for modular scaling

For example, the coordinator might determine a query needs both RAG retrieval and a specialized fine-tuned model, then orchestrate those calls. Both human users and other AI services can also directly call specific endpoints when they know what they need.

TL;DR The pytorch/CUDA work is for model optimization, quantization, and custom training, not for runtime inference.


### **AdventurousSwim1312** *( 5mo ago )*

Nah, honestly if you want a good framework, take a look at mirascope or dspy,

Langchain is popular essentially because they were first, but it's also a pile of poor abstraction choices and technical debt, good playground to learn, but much less for production.


### **Amazing_Trace** *( 5mo ago )*

Was it a business facing role?

They might not want people that will build a difficult to maintain core suite.


### **dougeeai** *( 5mo ago )*

It was actually a leadership role they were looking for someone with both strategy and technical backgrounds. I was a DS manager for years, pivoted back to IC a few years back to get my nails dirty with AI (and been loving it as intense as its been). So it seemed like a good fit, until today lol. Yeah the interviewer explicitly mentioned they aren't there to build AI models. But then why call me not technical enough?


### **Amazing_Trace** *( 5mo ago )*

this is what Josh Johnson calls "crackhead logic"


### **WolfeheartGames** *( 5mo ago )*

They invented an excuse to not tell you the real reason. They're afraid of working with your code. They want high level abstraction and are afraid of optimized solutions because math is scary.

This is valuable insight to you. While what you're doing is superior, it makes it harder to market yourself if you don't show both. Sometimes you'll be too smart/educated for a job, and that happens.


### **dougeeai** *( 5mo ago )*

Yeah this totally crossed my mind. Hell I've sometimes even gotten push back at my current work for going this route versus using langchain/ollama or just calling on frontier APIs.


### **WolfeheartGames** *( 5mo ago )*

As we move forward with agentic Ai, the idea of human comfort in code will be reduced. Focusing on optimization will be the ideal every programmer should aim for. This mindset and knowledge base will make you significantly more valuable as agentic coding improves.

A lot of optimization comes from creative thinking based on experience. I hope agentic coding doesn't reduce this capacity, but instead improves it. Giving over thinking to the machine will hamper this sort of progression.


### **igorwarzocha** *( 5mo ago )*

Ugh this only shows how crap the job market is. GPT writes for biz owners, hr people, recruiters and applicants. And nobody really knows what they're recruiting for in the end.

I'm on the other side of the spectrum, I'm looking for biz automation roles and... they all list low level frameworks as if every company that needs to plug an API and create an SOP that uses genAI was developing a SOTA model and an inference engine.

One day people are gonna get educated on how to use AI for recruitment, but it will be rough for a while. Good luck.


### **Minute_Attempt3063** *( 5mo ago )*

That company likely doesn't give a shit about good stuff.

See how they are just relying on API? Lazy shits.

It's fine to some degree, but looks like they are just depending on it to always work


### **[deleted]** *( 5mo ago )*

When you get disqualified for daft stuff it's usually a fake / stimulus job.

Intended for someone who isn't you but advertised nationally.

They're super annoying.


### **pico8lispr** *( 5mo ago )*

You're better off. The people who chase the framework rabbit don't get anything done. There are too many people asking, "whats new" not "what does it give me".


### **DerFreudster** *( 5mo ago )*

Glad to read the comments here, that was one of the first frameworks I tried and it was so complicated I started to question myself. Then worked with other things....better...


### **victorc25** *( 5mo ago )*

That means they use Langchain and probably the guy that installed it left, they just need someone to do something with it


### **sammcj** *( 5mo ago )*

🦙 llama.cpp

That's quite funny (of them). When I'm interviewing candidates I'm usually a little put off if they /do/ use LangChain and it can be a sign their knowledge is a bit dated. At the very least I'll probe a bit deeper than usual and ask them to explain what some of the potential issues with using it may be (looking for commentary about tight coupling, over-complicating etc etc). Really these days I'm quite disappointed and sceptical when I see that ecosystem used.

For me it's not as much a red flag if someone knows the LangChain ecosystem - it is a warning sign if they choose to use it however.

Frameworks all have pros and cons and while you can build something that "works" in most of them there are some that over complicate, over-abstract, and constraining. I recommend people learn a bit of whatever the most popular more modern frameworks are at a given time, and have knowledge without using any framework to round things out.


### **hello5346** *( 5mo ago )*

It is bloatware enforcing a vendor lock in. No essential tech here.


### **Impossible-Bake3866** *( 5mo ago )*

Dodged a bullet


### **Rude-Television8818** *( 5mo ago )*

Thing is Langchain/Langgraph has became a standard. Even if thoses frameworks are far from perfection, we have to use them anyway


### **TXT2** *( 5mo ago )*

I really don't get the LangGraph hate here. Langchain sucks that I agree but LangGraph is just a graph library with some helpers.

Also I don't understand how pytorch/cuda/gguf is relevant when designing multi-lagent systems. Most of the companies use apis directly or serve models with vllm. You are not beating vllm with your custom cuda code.


### **One-Employment3759** *( 5mo ago )*

remember, b-players don't hire a-players


### **tedivm** *( 5mo ago )*

I've been in this space as a hiring manager for a long time (joined Vicarious AI as VP of Eng in 2014, Rad AI in 2018, etc).

The people who interviewed you are idiots.

Anyone who is capable of using the lower level systems would have absolutely no problem learning a framework like LangChain. If you were to do a single weekend project with it, using your underlying ML knowledge, you'd probably be able to answer any of their questions. For the interviewers to focus on the framework and not the concepts shows that they themselves have a poor understanding of the concepts.

That said I think you dodged a bullet in another way. If a company is focused on LangChain they're probably focused on building AI applications. However, if you have solid CUDA and other low level knowledge companies that are focusing on actual model development, hosting, mlops, etc would find you way more valuable and probably pay you better for having those specialized skills. Knowing the low level parts of model development and optimization is a rare and valuable skill and you should focus on that in your job hunt.


### **vicks9880** *( 5mo ago )*

You dodged the bullet , imagine working in company and getting stuck to just using these bloated libraries without knowing the foundation, and just limiting yourself to specific libraries


### **JumpyAbies** *( 5mo ago )*

Stupid people dominate. You failed because you were smarter than them. They don't understand and are too stupid to know they're stupid, so they reject you. I think it was for the best; it's very difficult to work with stupid people, they always think they're right.


### **Regular-Forever5876** *( 5mo ago )*

Dodged a bullet.

They ask for an ML AI engineer, actually requires a Langchaon technician. Engineer known foundations and can/must bebable to learn and use anything around those foundations. Technicians are highly specialised employees over a very specific task.

One is white collar, the second is blue collar. Knowing the difference is outstanding. Ignoring it is a major red flag.

Failing to differentiate the two signals a lack of engineering maturity. It usually reveals gaps in technical leadership, role taxonomy, compensation mapping AND hiring governance. When a company labels a high-leverage engineering role as a task-based technician job, it usually indicates one of three things: misaligned expectations, unclear product strategy or a misunderstanding of where the real complexity sits in an AI stack.

You won a lottery ticket, go celebrate


### **Active-Picture-5681** *( 5mo ago )*

Bro I am a noob vibecoder and I can tell they are dumber than me


### **dougeeai** *( 5mo ago )*

Hey I'm certainly not going to act like I'm better than you. Even with years of Python experience Claude still codes faster than me - I lean on it hard too. Gotta watch it ofc, But I'll say this -> Every day of the year I'd vibe code with pytorch/cuda/or ggufs over handcoding in "simpler" frameworks.


### **twilight-actual** *( 5mo ago )*

What about Haystack? I've had a much better experience with Haystack than LangChain.