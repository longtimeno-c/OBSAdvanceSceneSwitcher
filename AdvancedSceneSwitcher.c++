#include <obs-module.h>
#include <obs-frontend-api.h>
#include <QTimer>
#include <QWidget>
#include <QVBoxLayout>
#include <QPushButton>
#include <QListWidget>
#include <QLineEdit>
#include <QLabel>
#include <map>
#include <vector>
#include <string>
#include <fstream>
#include <nlohmann/json.hpp> // JSON library (https://github.com/nlohmann/json)

using json = nlohmann::json;

static const char *plugin_name = "AdvancedSceneSwitcher";
static const char *config_file = "scene_groups.json";

struct SceneGroup {
    std::vector<std::string> scenes;
};

class SceneSwitcher : public QWidget {
    Q_OBJECT

private:
    QTimer timer;
    std::map<std::string, SceneGroup> sceneGroups;
    std::string currentGroup;
    int switchInterval = 30000; // Default 30 seconds
    QLabel *errorLabel;

    void displayError(const std::string &message) {
        errorLabel->setText(QString::fromStdString(message));
        errorLabel->setStyleSheet("color: red;");
        blog(LOG_ERROR, "AdvancedSceneSwitcher Error: %s", message.c_str());
    }

    void saveGroupsToFile() {
        try {
            char *config_path = obs_module_config_path(config_file);
            if (!config_path) throw std::runtime_error("Failed to get config path.");

            json j;
            for (const auto &group : sceneGroups) {
                j[group.first] = group.second.scenes;
            }
            std::ofstream file(config_path);
            if (!file.is_open()) throw std::runtime_error("Failed to open config file for writing.");

            file << j.dump(4);
            bfree(config_path);
        } catch (const std::exception &e) {
            displayError(e.what());
        }
    }

    void loadGroupsFromFile() {
        try {
            char *config_path = obs_module_config_path(config_file);
            if (!config_path) throw std::runtime_error("Failed to get config path.");

            std::ifstream file(config_path);
            if (!file.is_open()) throw std::runtime_error("Failed to open config file for reading.");

            json j;
            file >> j;
            for (const auto &item : j.items()) {
                sceneGroups[item.key()] = {item.value().get<std::vector<std::string>>()};
            }
            bfree(config_path);
        } catch (const std::exception &e) {
            displayError(e.what());
        }
    }

public:
    SceneSwitcher(QWidget *parent = nullptr) : QWidget(parent) {
        QVBoxLayout *layout = new QVBoxLayout(this);

        QPushButton *enableButton = new QPushButton("Enable Plugin", this);
        QPushButton *disableButton = new QPushButton("Disable Plugin", this);

        connect(enableButton, &QPushButton::clicked, this, &SceneSwitcher::enablePlugin);
        connect(disableButton, &QPushButton::clicked, this, &SceneSwitcher::disablePlugin);

        QListWidget *sceneGroupList = new QListWidget(this);
        QPushButton *addGroupButton = new QPushButton("Add Group", this);
        QPushButton *removeGroupButton = new QPushButton("Remove Group", this);

        layout->addWidget(enableButton);
        layout->addWidget(disableButton);
        layout->addWidget(sceneGroupList);
        layout->addWidget(addGroupButton);
        layout->addWidget(removeGroupButton);

        errorLabel = new QLabel(this);
        errorLabel->setText("");
        layout->addWidget(errorLabel);

        connect(&timer, &QTimer::timeout, this, &SceneSwitcher::switchScene);

        loadGroupsFromFile();
    }

    ~SceneSwitcher() {
        saveGroupsToFile();
    }

    void addSceneGroup(const std::string &groupName) {
        if (sceneGroups.find(groupName) == sceneGroups.end()) {
            sceneGroups[groupName] = SceneGroup{};
        }
    }

    void removeSceneGroup(const std::string &groupName) {
        sceneGroups.erase(groupName);
    }

    void setSwitchInterval(int interval) {
        switchInterval = interval;
        timer.setInterval(switchInterval);
    }

    void enablePlugin() {
        timer.start(switchInterval);
    }

    void disablePlugin() {
        timer.stop();
    }

    void switchScene() {
        try {
            if (currentGroup.empty() || sceneGroups[currentGroup].scenes.empty()) return;

            static size_t currentIndex = 0;
            const auto &scenes = sceneGroups[currentGroup].scenes;

            currentIndex = (currentIndex + 1) % scenes.size();
            obs_task_schedule([=]() {
                obs_scene_t *scene = obs_scene_by_name(scenes[currentIndex].c_str());
                if (!scene) throw std::runtime_error("Scene not found: " + scenes[currentIndex]);
                obs_frontend_set_current_scene(scene);
            });
        } catch (const std::exception &e) {
            displayError(e.what());
        }
    }

    void setActiveGroup(const std::string &groupName) {
        if (sceneGroups.find(groupName) != sceneGroups.end()) {
            currentGroup = groupName;
        } else {
            displayError("Group not found: " + groupName);
        }
    }
};

static SceneSwitcher *sceneSwitcherInstance = nullptr;

OBS_DECLARE_MODULE();
OBS_MODULE_USE_DEFAULT_LOCALE(plugin_name, "en-US");

bool obs_module_load(void) {
    sceneSwitcherInstance = new SceneSwitcher();

    obs_frontend_add_tools_menu_item("Advanced Scene Switcher", []() {
        sceneSwitcherInstance->show();
    });

    blog(LOG_INFO, "Advanced Scene Switcher loaded successfully.");
    return true;
}

void obs_module_unload(void) {
    delete sceneSwitcherInstance;
    sceneSwitcherInstance = nullptr;
}
