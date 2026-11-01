function sideButton(name: string) {
    return <button className="w-full text-left px-4 py-2 hover:bg-gray-200 focus:outline-none focus:bg-gray-200" onClick={() => console.log(name)}>
                {name}  
        </button>;
}

const sideBarElements = [
    sideButton("Search"),
    sideButton("Dictionary"),
    sideButton("Benchmark"),
    
]

function onClick(self: any) {
    document.getElementById("sidebar")?.classList.remove("active");
    self.classList.toggle("active");
}

for (let i = 0; i < sideBarElements.length; i++) {
    sideBarElements[i] = <div key={i}>{sideBarElements[i]}</div>
}