import Layout from './components/Layout'
import { ProjectProvider } from './api/context'

function App() {
    return (
        <ProjectProvider>
            <Layout />
        </ProjectProvider>
    )
}

export default App
