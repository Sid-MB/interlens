
## Documentation
See web documentation (auto rebuilt for the `main` branch) at <https://interlens.sidmb.com/llms-full.txt>.

## Contributing

Definitely contribute to interlens if you have any ideas or if you need any functionality at all that it doesn't have. Definitely do not do hacks in your own code or duplicate code when something could be done easier as part of interlens. This includes adding new models, new interp tools, and more.

## Conventions
Add full docstrings to every class, every method, and every parameter, especially in publically exposed APIs beacuse it will automatically become our documentation. Keep docstrings simple and terse, but make sure they also share the implementation details of what is going on under-the-hood.

### Coding Tips
- If two classes share the same parameters, they should probably be the same class. For example, instead of a `ConversationTemplate` and a `Conversation`, if they both have the same params, just have a lightweight `Conversation` object. If it needs to store heavier information, there can be internal lazy-loaded info that the client doesn't have to deal with. There should not be many wrapper classes or similar needed or visible to the client. 
- Simplicity, subtraction, and ease of use is key. Implementing using the library should feel intuitive and beautiful.
	- Continue refactoring and simplifying repeatedly during the planning and coding stage until you get here
- By default, gpu runs should be as performant as possible with optimizations for running across gpus if multiple are available, running multiple rollouts at the same time on a single gpu, etc. I know that with some of the advanced interp stuff, this may not be possible and that is fine.

### Documentation
Write documentation along with code. Documentation should be __clean__, __simple to follow__, and include __worked examples__. Generally, documentation should have at least one example which shows how all of the possible parameters can be used, and it should show what outputs look like. 

