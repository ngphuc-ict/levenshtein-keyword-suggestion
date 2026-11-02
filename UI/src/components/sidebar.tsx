function sideButton(name: string) {
    return <button className="w-full text-left px-4 py-2 hover:bg-gray-200 focus:outline-none focus:bg-gray-200" onClick={(e) => onClickHandler(e.currentTarget as HTMLElement)}>
                {name}  
        </button>;
}

const sideBarElements = [
    sideButton("Search"),
    sideButton("Dictionary"),
    sideButton("Benchmark"),
    
]

function onClickHandler(self: HTMLElement) {
    self.classList.add("active");
    for (const sibling of self.parentElement!.children) {
        if (sibling !== self) {
            sibling.classList.remove("active");
        }
    }
}

function Sidebar() {
    return (
        <div className="w-64 bg-gray-100 h-screen p-4">
            {sideBarElements}
        </div>
    );
}

export default Sidebar;